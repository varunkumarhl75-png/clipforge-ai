from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import json
import shutil
import threading
import logging

from app.db.database import get_db, SessionLocal
from app.models import *
from app.schemas import *

from app.services import (
    generate_project_id,
    validate_video_file,
    get_project_upload_dir,
    check_ffmpeg_available,
)

from app.services.job_processor import processor
from app.services.ai_service import transcribe_audio, repurpose
from app.services.youtube_service import download_youtube
from app.services.caption_service import write_captions
from app.services.short_service import suggest_windows, create_short
from app.services.multimodal_analysis import analyze_video
from app.services.edit_service import render_edit
from app.services.youtube_publish_service import publish_video
from app.services.content_service import ContentProviderError, get_content_provider
from app.services.generation_service import generate_image, generate_video
from app.services.ai import get_ai_provider
from app.services.ai.base import AIProviderError
from app.core import settings

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api",
    tags=["NyxarClip"]
)

@router.post('/generate/image')
@router.post('/generate/thumbnail')
def generate_ai_image(data: GenerateRequest):
    try:
        provider = get_ai_provider()
        image = provider.generate_image(data.prompt)
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    extension = '.jpg' if image.media_type == 'image/jpeg' else '.png'
    output_dir = Path(settings.PROCESSED_DIR) / 'ai' / 'images'
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f'{uuid.uuid4().hex}{extension}'
    path.write_bytes(image.data)
    return {'success': True, 'provider': provider.name, 'media_url': f'/api/generate/media/{path.name}', 'media_type': image.media_type}

@router.post('/generate/video')
@router.post('/generate/short-video')
def generate_ai_video(data: GenerateRequest):
    path = generate_video(data.prompt, data.aspect_ratio)
    return {'success': True, 'media_url': f'/api/generate/media/{Path(path).name}', 'media_type': 'video'}

@router.get('/generate/media/{media_name}')
def generated_media(media_name: str):
    for directory in ('images', 'videos'):
        candidate = Path(settings.PROCESSED_DIR) / 'ai' / directory / media_name
        if candidate.is_file() and candidate.name == media_name:
            media_type = 'video/mp4' if directory == 'videos' else ('image/jpeg' if candidate.suffix.lower() in {'.jpg', '.jpeg'} else 'image/png')
            return FileResponse(candidate, media_type=media_type)
    raise HTTPException(status_code=404, detail='Generated media not found')


# ============================================================
# HELPER
# ============================================================

def get_project(pid: str, db: Session):
    project = (
        db.query(Project)
        .filter(Project.id == pid)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return project


# ============================================================
# HEALTH
# ============================================================

@router.get("/health")
def health():
    return {
        "status": "ok",
        "message": "NyxarClip AI backend is running",
        "ffmpeg_available": check_ffmpeg_available(),
        "features": [
            "transcription",
            "shorts",
            "captions",
            "editing",
            "repurposing",
            "analytics",
            "youtube",
        ],
    }


# ============================================================
# PROJECTS
# ============================================================

@router.post(
    "/projects",
    response_model=ProjectResponse
)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db)
):
    project = Project(
        id=generate_project_id(),
        name=data.name,
        source_type=data.source_type,
        source_url=data.source_url,
        status="pending",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get(
    "/projects",
    response_model=list[ProjectResponse]
)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/projects/{pid}",
    response_model=ProjectResponse
)
def get_project_route(
    pid: str,
    db: Session = Depends(get_db)
):
    return get_project(pid, db)


# ============================================================
# DELETE PROJECT
# ============================================================

@router.delete("/projects/{pid}")
def delete_project(
    pid: str,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    upload_dir = Path(settings.UPLOAD_DIR) / pid

    if upload_dir.exists():
        shutil.rmtree(
            upload_dir,
            ignore_errors=True
        )

    for directory in [
        "thumbnails",
        "audio",
        "captions",
        "shorts",
        "edits",
    ]:
        processed_dir = (
            Path(settings.PROCESSED_DIR) / directory
        )

        if processed_dir.exists():
            project_directory = processed_dir / pid
            if project_directory.is_dir():
                shutil.rmtree(project_directory, ignore_errors=True)
            for file in processed_dir.glob(
                f"{pid}*"
            ):
                file.unlink(
                    missing_ok=True
                )

    db.delete(project)
    db.commit()

    return {
        "ok": True
    }


# ============================================================
# VIDEO UPLOAD
# ============================================================

@router.post(
    "/projects/{pid}/upload",
    response_model=VideoUploadResponse
)
async def upload(
    pid: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = get_project(pid, db)

    filename = file.filename or "video.mp4"

    # Validate extension first.
    ok, message = validate_video_file(
        filename,
        0
    )

    if not ok:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    upload_dir = get_project_upload_dir(pid)

    extension = (
        Path(filename).suffix.lower()
        or ".mp4"
    )

    file_path = (
        upload_dir / f"original{extension}"
    )

    size = 0

    try:
        with file_path.open("wb") as output:

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                size += len(chunk)

                if size > settings.UPLOAD_MAX_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Video exceeds 5GB limit"
                    )

                output.write(chunk)

        project.original_filename = filename
        project.video_file_path = str(file_path)
        project.source_type = "upload"
        project.status = "queued"
        project.processing_progress = 0
        project.processing_step = "Queued"

        db.commit()

        processor.process_video_async(pid)

        return {
            "project_id": pid,
            "filename": filename,
            "file_path": str(file_path),
            "status": "queued",
        }

    except HTTPException:
        file_path.unlink(
            missing_ok=True
        )
        raise

    except Exception as exc:
        file_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}"
        )


# ============================================================
# YOUTUBE
# ============================================================

@router.post(
    "/projects/{pid}/youtube",
    response_model=VideoUploadResponse
)
def youtube(
    pid: str,
    data: YouTubeImportRequest,
    db: Session = Depends(get_db),
):
    project = get_project(pid, db)

    try:
        path, info = download_youtube(
            data.url,
            str(get_project_upload_dir(pid))
        )
        if not Path(path).is_file():
            raise RuntimeError('YouTube import completed without producing a video file')

        title = info.get(
            "title",
            "YouTube video"
        )

        project.source_type = "youtube_url"
        project.source_url = data.url
        project.original_filename = (
            f"{title}.mp4"
        )
        project.video_file_path = path
        project.status = "queued"
        project.processing_step = "Queued"

        db.commit()

        processor.process_video_async(pid)

        return {
            "project_id": pid,
            "filename": project.original_filename,
            "file_path": path,
            "status": "queued",
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"YouTube import failed: {exc}"
        )


# ============================================================
# YOUTUBE PUBLISH
# ============================================================

@router.post(
    "/projects/{pid}/youtube/publish"
)
def youtube_publish(
    pid: str,
    data: YouTubePublishRequest,
    db: Session = Depends(get_db),
):
    project = get_project(pid, db)

    if not project.video_file_path:
        raise HTTPException(
            status_code=400,
            detail="Project has no video"
        )

    try:
        return publish_video(
            project.video_file_path,
            data.access_token,
            data.title,
            data.description,
            data.privacy_status,
            data.tags,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=f"YouTube publish failed: {exc}"
        )


# ============================================================
# PROCESSING STATUS
# ============================================================

@router.get(
    "/projects/{pid}/status"
)
def status(
    pid: str,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    return {
        "project_id": pid,
        "status": project.status,
        "progress": project.processing_progress or 0,
        "step": project.processing_step,
        "error_message": project.error_message,
    }


# ============================================================
# VIDEO
# ============================================================

@router.get(
    "/projects/{pid}/video"
)
def video(
    pid: str,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    file_path = Path(
        project.video_file_path or ""
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Video not found"
        )

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=(
            project.original_filename
            or "video.mp4"
        ),
    )


# ============================================================
# THUMBNAIL
# ============================================================

@router.get(
    "/projects/{pid}/thumbnail"
)
def thumbnail(
    pid: str,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    file_path = Path(
        project.thumbnail_path or ""
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Thumbnail not available"
        )

    media_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(file_path, media_type=media_type)


@router.get("/projects/{pid}/thumbnail/generated/{filename}")
def generated_project_thumbnail(pid: str, filename: str, db: Session = Depends(get_db)):
    get_project(pid, db)
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    output_dir = (Path(settings.PROCESSED_DIR) / "thumbnails" / pid / "generated").resolve()
    file_path = (output_dir / filename).resolve()
    if output_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    media_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(file_path, media_type=media_type, filename="nyxarclip-thumbnail" + file_path.suffix.lower())


@router.post("/projects/{pid}/thumbnail")
@router.post("/projects/{pid}/thumbnail/generate")
def generate_project_thumbnail(
    pid: str,
    data: ThumbnailGenerateRequest,
    db: Session = Depends(get_db),
):
    project = get_project(pid, db)
    prompt = data.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Thumbnail prompt cannot be empty.")
    try:
        provider = get_ai_provider()
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    context = (
        "Create a professional 16:9 YouTube thumbnail. Use a strong focal subject, clear visual hierarchy, "
        "high contrast, polished lighting, and a clean composition. Do not add claims or text unless the user requests it. "
        f"Project context: {project.name}. User instruction: {prompt}"
    )
    try:
        image = provider.generate_image(context)
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    extension = ".jpg" if image.media_type == "image/jpeg" else ".png"
    if image.media_type not in {"image/png", "image/jpeg"} or not image.data:
        raise HTTPException(status_code=502, detail="Thumbnail generation failed. Please try again.")
    output_dir = Path(settings.PROCESSED_DIR) / "thumbnails" / pid / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"generated-{uuid.uuid4().hex}{extension}"
    output_path.write_bytes(image.data)
    project.thumbnail_path = str(output_path)
    db.commit()
    return {
        "project_id": pid,
        "provider": provider.name,
        "media_url": f"/api/projects/{pid}/thumbnail/generated/{output_path.name}",
        "media_type": image.media_type,
        "status": "ready",
    }


# ============================================================
# AUDIO
# ============================================================

@router.get(
    "/projects/{pid}/audio"
)
def audio(
    pid: str,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    file_path = Path(
        project.audio_path or ""
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio not available"
        )

    return FileResponse(
        file_path,
        media_type="audio/wav"
    )


# ============================================================
# TRANSCRIPTION
# ============================================================

@router.post(
    "/projects/{pid}/transcribe"
)
def transcribe(
    pid: str,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    if (
        not project.audio_path
        or not Path(project.audio_path).exists()
    ):
        raise HTTPException(
            status_code=400,
            detail="Audio is not ready yet"
        )

    try:

        result = transcribe_audio(
            project.audio_path,
            settings.WHISPER_MODEL
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

    # Remove previous transcript.
    db.query(
        TranscriptSegment
    ).filter_by(
        project_id=pid
    ).delete()

    db.query(
        Transcript
    ).filter_by(
        project_id=pid
    ).delete()

    transcript = Transcript(
        project_id=pid,
        language=result["language"],
        full_text=result["text"],
        status="completed",
    )

    db.add(transcript)

    # Save every Whisper segment.
    for segment in result["segments"]:

        db.add(
            TranscriptSegment(
                project_id=pid,
                start=float(segment["start"]),
                end=float(segment["end"]),
                text=segment["text"],
            )
        )

    db.commit()

    return {
        "project_id": pid,
        **result,
    }


# ============================================================
# GET TRANSCRIPT
# ============================================================

@router.get(
    "/projects/{pid}/transcript"
)
def get_transcript(
    pid: str,
    db: Session = Depends(get_db)
):
    get_project(pid, db)

    transcript = (
        db.query(Transcript)
        .filter_by(project_id=pid)
        .order_by(Transcript.id.desc())
        .first()
    )

    segments = (
        db.query(TranscriptSegment)
        .filter_by(project_id=pid)
        .order_by(TranscriptSegment.start)
        .all()
    )

    return {
        "text": (
            transcript.full_text
            if transcript
            else ""
        ),
        "language": (
            transcript.language
            if transcript
            else "en"
        ),
        "status": (
            transcript.status
            if transcript
            else "missing"
        ),
        "segments": [
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": segment.text,
            }
            for segment in segments
        ],
    }


# ============================================================
# CHAPTERS AND CONTENT PACKAGE
# ============================================================

@router.post('/projects/{pid}/chapters', response_model=list[ChapterResponse])
def generate_chapters(pid: str, db: Session = Depends(get_db)):
    get_project(pid, db)
    segments = db.query(TranscriptSegment).filter_by(project_id=pid).order_by(TranscriptSegment.start).all()
    if not segments:
        raise HTTPException(status_code=400, detail='Generate a transcript first')
    db.query(Chapter).filter_by(project_id=pid).delete()
    chapters = []
    last_start = -60.0
    for segment in segments:
        if float(segment.start) - last_start >= 60 or not chapters:
            title = ' '.join((segment.text or '').split())[:70].rstrip('.!?') or 'Chapter'
            chapter = Chapter(project_id=pid, start_time=float(segment.start), title=title)
            db.add(chapter)
            chapters.append(chapter)
            last_start = float(segment.start)
    db.commit()
    for chapter in chapters:
        db.refresh(chapter)
    return chapters


@router.get('/projects/{pid}/chapters', response_model=list[ChapterResponse])
def list_chapters(pid: str, db: Session = Depends(get_db)):
    get_project(pid, db)
    return db.query(Chapter).filter_by(project_id=pid).order_by(Chapter.start_time).all()


@router.post('/projects/{pid}/content-package', response_model=ContentPackageResponse)
def generate_content_package(pid: str, db: Session = Depends(get_db)):
    get_project(pid, db)
    transcript = db.query(Transcript).filter_by(project_id=pid).order_by(Transcript.id.desc()).first()
    if not transcript or not transcript.full_text:
        raise HTTPException(status_code=400, detail='Generate a transcript first')
    provider = get_content_provider()
    try:
        result = provider.generate(transcript.full_text)
    except ContentProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    package = ContentPackage(project_id=pid, provider=provider.name, status='completed', **result)
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.get('/projects/{pid}/content-package', response_model=ContentPackageResponse | None)
def get_content_package(pid: str, db: Session = Depends(get_db)):
    get_project(pid, db)
    return db.query(ContentPackage).filter_by(project_id=pid).order_by(ContentPackage.id.desc()).first()


# ============================================================
# CAPTIONS
# ============================================================

@router.post(
    "/projects/{pid}/captions"
)
def captions(
    pid: str,
    db: Session = Depends(get_db)
):
    """
    Generate SRT and VTT caption files from
    stored Whisper transcript segments.
    """

    get_project(pid, db)

    segments_db = (
        db.query(TranscriptSegment)
        .filter_by(project_id=pid)
        .order_by(TranscriptSegment.start)
        .all()
    )

    usable_segments = [segment for segment in segments_db if (segment.text or "").strip()]
    if not usable_segments:
        raise HTTPException(
            status_code=400,
            detail="Generate a transcript first. No speech segments are available."
        )

    segments = [
        {
            "start": float(segment.start),
            "end": float(segment.end),
            "text": segment.text,
        }
        for segment in usable_segments
    ]

    captions_dir = (
        Path(settings.PROCESSED_DIR)
        / "captions"
    )

    captions_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    try:

        srt_path, vtt_path = write_captions(
            pid,
            segments,
            captions_dir
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Caption generation failed: {exc}"
        )

    caption = db.query(Caption).filter_by(project_id=pid).order_by(Caption.id.asc()).first()
    if caption is None:
        caption = Caption(project_id=pid)
        db.add(caption)
    caption.srt_path = str(srt_path)
    caption.vtt_path = str(vtt_path)
    caption.status = "ready"
    db.commit()
    db.refresh(caption)

    return _caption_response(pid, caption, len(segments), db)


def _caption_response(pid: str, caption: Caption, segment_count: int, db: Session):
    transcript = db.query(Transcript).filter_by(project_id=pid).order_by(Transcript.id.desc()).first()
    return {
        "project_id": pid,
        "status": caption.status,
        "language": transcript.language if transcript else "en",
        "segment_count": segment_count,
        "srt": f"/api/projects/{pid}/captions/srt",
        "vtt": f"/api/projects/{pid}/captions/vtt",
    }


@router.get("/projects/{pid}/captions")
def get_captions(pid: str, db: Session = Depends(get_db)):
    get_project(pid, db)
    caption = db.query(Caption).filter_by(project_id=pid).order_by(Caption.id.desc()).first()
    if not caption:
        raise HTTPException(status_code=404, detail="Captions not available")
    segment_count = db.query(TranscriptSegment).filter(
        TranscriptSegment.project_id == pid,
        TranscriptSegment.text.is_not(None),
        TranscriptSegment.text != "",
    ).count()
    return _caption_response(pid, caption, segment_count, db)


# ============================================================
# DOWNLOAD CAPTION FILE
# ============================================================

@router.get(
    "/projects/{pid}/captions/{kind}"
)
def caption_file(
    pid: str,
    kind: str,
    db: Session = Depends(get_db)
):
    get_project(pid, db)

    if kind not in {"srt", "vtt"}:
        raise HTTPException(
            status_code=400,
            detail="Caption format must be srt or vtt"
        )

    caption = (
        db.query(Caption)
        .filter_by(project_id=pid)
        .order_by(Caption.id.desc())
        .first()
    )

    if not caption:
        raise HTTPException(
            status_code=404,
            detail="Captions not available"
        )

    file_path = Path(
        caption.srt_path
        if kind == "srt"
        else caption.vtt_path
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Caption file not found"
        )

    media_type = (
        "application/x-subrip"
        if kind == "srt"
        else "text/vtt"
    )

    return FileResponse(
        file_path,
        media_type=media_type,
        filename=(
            f"{pid}.{kind}"
        ),
    )


# ============================================================
# SHORTS
# ============================================================

def _render_short(short_id: str, project_id: str, video_path: str, output_path: str, caption_path: str | None, remove_silence: bool, export_quality: str):
    worker_db = SessionLocal()
    try:
        short = worker_db.query(Short).filter_by(id=short_id).first()
        if not short:
            return
        short.status = 'processing'
        worker_db.commit()
        create_short(video_path, short.start, short.duration, output_path, caption_path=caption_path, remove_silence=remove_silence, export_quality=export_quality)
        if not Path(output_path).is_file() or Path(output_path).stat().st_size == 0:
            raise RuntimeError('Short renderer did not produce an output file')
        short.video_path = output_path
        short.status = 'completed'
        worker_db.commit()
    except Exception as exc:
        logger.exception('Short rendering failed for %s', short_id)
        short = worker_db.query(Short).filter_by(id=short_id).first()
        if short:
            short.status = 'failed'
            short.reason = f'Rendering failed: {exc}'
            worker_db.commit()
    finally:
        worker_db.close()

@router.post(
    "/projects/{pid}/shorts"
)
def generate_shorts(
    pid: str,
    data: ShortsRequest | None = None,
    max_shorts: int | None = None,
    limit: int | None = None,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    if not project.video_file_path or not Path(project.video_file_path).is_file():
        raise HTTPException(status_code=400, detail='Project video is not ready')

    segments = (
        db.query(TranscriptSegment)
        .filter_by(project_id=pid)
        .order_by(TranscriptSegment.start)
        .all()
    )

    transcript_segments = [
        {
            "start": float(segment.start),
            "end": float(segment.end),
            "text": segment.text,
        }
        for segment in segments
    ]

    count = data.count if data else 10
    if data and data.max_shorts is not None:
        count = data.max_shorts
    if data and data.limit is not None:
        count = data.limit
    count = limit or max_shorts or count or 10
    windows = analyze_video(project.video_file_path, project.duration or 0, transcript_segments, max_candidates=count)

    created = []

    for candidate in windows[:count]:
        start, duration, hook = candidate.start, candidate.duration, candidate.hook

        short_id = str(uuid.uuid4())

        output = (
            Path(settings.PROCESSED_DIR)
            / "shorts"
            / f"{short_id}.mp4"
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        clean_hook = ' '.join(hook.split())
        score = round(candidate.score * 100, 1)
        reason = candidate.reason
        short = Short(
            id=short_id,
            project_id=pid,
            title=(
                f"Clip {len(created) + 1}: "
                f"{hook[:55]}"
            ),
            start=start,
            duration=min(
                duration,
                (project.duration or 0) - start
            ),
            video_path=None,
            hook=clean_hook,
            score=score,
            reason=reason,
            category=candidate.category,
            subcategories=candidate.subcategories,
            confidence=candidate.confidence,
            signals=candidate.signals,
            detected_events=candidate.detected_events,
            warnings=candidate.warnings,
            analysis_source=candidate.analysis_source,
            status='queued',
        )

        db.add(short)
        created.append(short)

    db.commit()

    caption = db.query(Caption).filter_by(project_id=pid).order_by(Caption.id.desc()).first()
    # Shorts are always delivered with hardcoded captions when a transcript exists.
    caption_path = caption.srt_path if caption and Path(caption.srt_path).is_file() else None
    if not caption_path and transcript_segments:
        fallback_caption_dir = Path(settings.TEMPORARY_DIR) / 'short-captions'
        caption_path, _ = write_captions(pid, transcript_segments, fallback_caption_dir)
    export_quality = data.export_quality if data else '1080p'
    for short in created:
        threading.Thread(target=_render_short, args=(short.id, pid, project.video_file_path, str(Path(settings.PROCESSED_DIR) / 'shorts' / f'{short.id}.mp4'), caption_path, bool(data and data.remove_silence), export_quality), daemon=True).start()

    return {
        "shorts": [
            {
                "id": short.id,
                "title": short.title,
                "start": short.start,
                "duration": short.duration,
                "hook": short.hook,
                "score": short.score,
                "reason": short.reason,
                "category": short.category,
                "subcategories": short.subcategories or [],
                "confidence": short.confidence,
                "signals": short.signals or {},
                "detected_events": short.detected_events or [],
                "warnings": short.warnings or [],
                "analysis_source": short.analysis_source or "local",
                "end": short.start + short.duration,
                "status": short.status,
            }
            for short in created
        ]
    }


@router.get(
    "/projects/{pid}/shorts"
)
def list_shorts(
    pid: str,
    db: Session = Depends(get_db)
):
    get_project(pid, db)

    shorts = (
        db.query(Short)
        .filter_by(project_id=pid)
        .order_by(Short.id)
        .all()
    )

    return [
        {
            "id": short.id,
            "title": short.title,
            "start": short.start,
            "duration": short.duration,
            "hook": short.hook,
            "score": short.score,
            "reason": short.reason,
            "category": short.category,
            "subcategories": short.subcategories or [],
            "confidence": short.confidence,
            "signals": short.signals or {},
            "detected_events": short.detected_events or [],
            "warnings": short.warnings or [],
            "analysis_source": short.analysis_source or "local",
            "end": short.start + short.duration,
            "status": short.status,
            "video_url": f"/api/shorts/{short.id}/video" if short.video_path and Path(short.video_path).is_file() else None,
        }
        for short in shorts
    ]


@router.get(
    "/shorts/{sid}/video"
)
def short_video(
    sid: str,
    db: Session = Depends(get_db)
):
    short = (
        db.query(Short)
        .filter_by(id=sid)
        .first()
    )

    file_path = (
        Path(short.video_path or "")
        if short
        else Path("")
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Short not available"
        )

    return FileResponse(
        file_path,
        media_type="video/mp4"
    )


# ============================================================
# REPURPOSE
# ============================================================

@router.post(
    "/projects/{pid}/repurpose"
)
def repurpose_project(
    pid: str,
    db: Session = Depends(get_db)
):
    get_project(pid, db)

    transcript = (
        db.query(Transcript)
        .filter_by(project_id=pid)
        .order_by(Transcript.id.desc())
        .first()
    )

    if (
        not transcript
        or not transcript.full_text
    ):
        raise HTTPException(
            status_code=400,
            detail="Generate a transcript first"
        )

    return {
        "ideas": repurpose(
            transcript.full_text,
            5
        )
    }


# ============================================================
# EDIT
# ============================================================

def _render_edit_job(job_id: str, video_path: str, spec: dict, output_path: str):
    worker_db = SessionLocal()
    try:
        job = worker_db.query(EditJob).filter_by(id=job_id).first()
        if not job:
            return
        job.status = 'processing'
        worker_db.commit()
        render_edit(video_path, spec, output_path)
        if not Path(output_path).is_file() or Path(output_path).stat().st_size == 0:
            raise RuntimeError('Edit renderer did not produce an output file')
        job.output_path = output_path
        job.status = 'completed'
        worker_db.commit()
    except Exception as exc:
        logger.exception('Edit rendering failed for %s', job_id)
        job = worker_db.query(EditJob).filter_by(id=job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(exc)
            worker_db.commit()
    finally:
        worker_db.close()

@router.post(
    "/projects/{pid}/edit"
)
def edit(
    pid: str,
    data: EditRequest,
    db: Session = Depends(get_db)
):
    project = get_project(pid, db)

    output = (
        Path(settings.PROCESSED_DIR)
        / "edits"
        / f"{uuid.uuid4()}.mp4"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    job = EditJob(
        id=str(uuid.uuid4()),
        project_id=pid,
        spec_json=json.dumps({**data.spec, 'export_quality': data.export_quality}),
        output_path=str(output),
        status="queued",
    )

    db.add(job)
    db.commit()

    threading.Thread(target=_render_edit_job, args=(job.id, project.video_file_path, {**data.spec, 'export_quality': data.export_quality}, str(output)), daemon=True).start()

    return {
        "id": job.id,
        "status": "queued",
        "video_url": None,
    }


@router.get('/edits/{eid}')
def edit_status(eid: str, db: Session = Depends(get_db)):
    job = db.query(EditJob).filter_by(id=eid).first()
    if not job:
        raise HTTPException(status_code=404, detail='Edit job not found')
    return {'id': job.id, 'status': job.status, 'error_message': job.error_message, 'video_url': f'/api/edits/{job.id}/video' if job.status == 'completed' and job.output_path and Path(job.output_path).is_file() else None}


@router.get(
    "/edits/{eid}/video"
)
def edit_video(
    eid: str,
    db: Session = Depends(get_db)
):
    job = (
        db.query(EditJob)
        .filter_by(id=eid)
        .first()
    )

    file_path = (
        Path(job.output_path or "")
        if job
        else Path("")
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Edited video not available"
        )

    return FileResponse(
        file_path,
        media_type="video/mp4"
    )


# ============================================================
# ANALYTICS
# ============================================================

@router.get("/analytics")
def analytics(
    db: Session = Depends(get_db)
):
    projects = db.query(Project).all()

    return {
        "total_projects": len(projects),
        "completed": sum(
            p.status == "completed"
            for p in projects
        ),
        "processing": sum(
            p.status in ("queued", "processing")
            for p in projects
        ),
        "failed": sum(
            p.status == "failed"
            for p in projects
        ),
        "total_duration": round(
            sum(
                p.duration or 0
                for p in projects
            ),
            2
        ),
        "shorts_generated": (
            db.query(Short).count()
        ),
        "transcripts": (
            db.query(Transcript).count()
        ),
        "captions": (
            db.query(Caption).count()
        ),
        "edits": (
            db.query(EditJob).count()
        ),
    }


@router.get('/settings')
def app_settings():
    return {
        'whisper_model': settings.WHISPER_MODEL,
        'ffmpeg_available': check_ffmpeg_available(),
        'demo_mode': settings.DEMO_MODE,
        'llm_configured': bool(settings.OPENAI_API_KEY),
        'youtube_configured': bool(settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET),
    }


# ============================================================
# CHANNEL
# ============================================================

@router.get("/channel")
def channel(
    db: Session = Depends(get_db)
):
    channel_setting = (
        db.query(ChannelSetting)
        .first()
    )

    if not channel_setting:
        return {
            "channel_name": "",
            "youtube_connected": False,
            "youtube_channel_id": None,
        }

    return {
        "channel_name": (
            channel_setting.channel_name
        ),
        "youtube_connected": (
            channel_setting.youtube_connected
        ),
        "youtube_channel_id": (
            channel_setting.youtube_channel_id
        ),
    }


@router.post("/channel")
def save_channel(
    data: ChannelRequest,
    db: Session = Depends(get_db)
):
    channel_setting = (
        db.query(ChannelSetting)
        .first()
    )

    if not channel_setting:
        channel_setting = ChannelSetting()

    channel_setting.channel_name = (
        data.channel_name
    )

    # A channel ID is metadata only; OAuth must explicitly verify a connection.
    channel_setting.youtube_connected = False

    channel_setting.youtube_channel_id = (
        data.youtube_channel_id
    )

    db.add(channel_setting)
    db.commit()
    db.refresh(channel_setting)

    return {
        "ok": True,
        "channel_name": (
            channel_setting.channel_name
        ),
        "youtube_connected": (
            channel_setting.youtube_connected
        ),
    }