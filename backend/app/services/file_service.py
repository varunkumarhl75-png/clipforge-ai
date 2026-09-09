import os
import uuid
from pathlib import Path
from app.core import settings


def ensure_storage_dirs():
    """Ensure all storage directories exist."""
    for directory in [
        settings.UPLOAD_DIR,
        settings.PROCESSED_DIR,
        Path(settings.PROCESSED_DIR) / "thumbnails",
        Path(settings.PROCESSED_DIR) / "audio",
        settings.TEMPORARY_DIR,
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)


def generate_project_id() -> str:
    """Generate a unique project ID."""
    return str(uuid.uuid4())


def generate_safe_filename(original_filename: str) -> str:
    """Generate a safe filename from the original."""
    # Get file extension
    _, ext = os.path.splitext(original_filename)
    
    # Generate safe name with UUID
    safe_name = f"{uuid.uuid4()}{ext.lower()}"
    return safe_name


def get_project_upload_dir(project_id: str) -> Path:
    """Get the upload directory for a project."""
    project_dir = Path(settings.UPLOAD_DIR) / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def get_video_file_path(project_id: str, filename: str) -> Path:
    """Get the video file path for a project."""
    return get_project_upload_dir(project_id) / filename


def validate_video_file(filename: str, file_size: int) -> tuple[bool, str]:
    """Validate video file.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Allowed video extensions
    allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
    
    # Check extension
    _, ext = os.path.splitext(filename)
    if ext.lower() not in allowed_extensions:
        return False, f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check file size
    if file_size > settings.UPLOAD_MAX_SIZE:
        max_gb = settings.UPLOAD_MAX_SIZE / (1024**3)
        return False, f"File size exceeds {max_gb:.1f}GB limit"
    
    return True, ""


def cleanup_project_files(project_id: str) -> None:
    """Clean up all files associated with a project."""
    # Delete upload directory
    upload_dir = get_project_upload_dir(project_id)
    if upload_dir.exists():
        for file in upload_dir.glob("*"):
            file.unlink()
        upload_dir.rmdir()
    
    # Delete thumbnail
    thumbnail_path = Path(settings.PROCESSED_DIR) / "thumbnails" / f"{project_id}.jpg"
    if thumbnail_path.exists():
        thumbnail_path.unlink()
    
    # Delete audio
    audio_path = Path(settings.PROCESSED_DIR) / "audio" / f"{project_id}.wav"
    if audio_path.exists():
        audio_path.unlink()

def cleanup_temp_files(*paths: str) -> None:
    for path in paths:
        try:
            p=Path(path)
            if p.exists(): p.unlink()
        except Exception:
            pass
