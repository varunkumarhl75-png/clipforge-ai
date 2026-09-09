import threading, logging, uuid
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models import Project, ProjectStatusEnum, ProcessingJob
from app.services.video_processor import extract_metadata,generate_thumbnail,extract_audio,InvalidVideoError,FFmpegNotFoundError
from app.core import settings
logger=logging.getLogger(__name__)
class JobProcessor:
    def process_video_async(self,project_id):
        db=SessionLocal()
        try:
            active=db.query(ProcessingJob).filter(ProcessingJob.project_id==project_id, ProcessingJob.status.in_(['queued','processing'])).first()
            if active:return active.id
            job=ProcessingJob(id=str(uuid.uuid4()),project_id=project_id,status='queued',progress=0,current_step='Queued')
            db.add(job);db.commit()
            threading.Thread(target=self._worker,args=(project_id,job.id),daemon=True).start()
            return job.id
        finally:db.close()
    def recover(self):
        db=SessionLocal()
        try:
            jobs=db.query(ProcessingJob).filter(ProcessingJob.status=='processing').all()
            for job in jobs:
                job.status='queued';job.current_step='Requeued after backend restart';job.error=None
                project=db.query(Project).filter(Project.id==job.project_id).first()
                if project:project.status='queued';project.processing_step='Requeued after backend restart'
            db.commit()
            for job in jobs: threading.Thread(target=self._worker,args=(job.project_id,job.id),daemon=True).start()
        finally:db.close()
    def _worker(self,pid,job_id):
        db=SessionLocal()
        try:
            p=db.query(Project).filter(Project.id==pid).first()
            if not p:return
            job=db.query(ProcessingJob).filter(ProcessingJob.id==job_id).first()
            p.status='processing';p.processing_progress=10;p.processing_step='Reading video metadata'
            if job:job.status='processing';job.progress=10;job.current_step=p.processing_step;job.started_at=datetime.utcnow()
            db.commit()
            meta=extract_metadata(p.video_file_path)
            for k in ['duration','width','height','fps','video_codec','audio_codec','bitrate','file_size','has_audio']: setattr(p,k,meta.get(k))
            p.processing_progress=35;p.processing_step='Generating thumbnail'
            if job:job.progress=35;job.current_step=p.processing_step
            db.commit()
            thumb=Path(settings.PROCESSED_DIR)/'thumbnails'/f'{pid}.jpg'
            if not generate_thumbnail(p.video_file_path,str(thumb)):
                raise RuntimeError('Thumbnail generation failed')
            p.thumbnail_path=str(thumb)
            p.processing_progress=55;p.processing_step='Extracting audio'
            if job:job.progress=55;job.current_step=p.processing_step
            db.commit()
            if p.has_audio:
                audio=Path(settings.PROCESSED_DIR)/'audio'/f'{pid}.wav'
                if not extract_audio(p.video_file_path,str(audio)):
                    raise RuntimeError('Audio extraction failed')
                p.audio_path=str(audio)
            else:
                p.processing_step='No audio track; transcription unavailable'
            p.processing_progress=80;p.processing_step='Ready for AI analysis';p.status='completed';p.processing_progress=100;p.processing_step='Completed'
            if job:job.status='completed';job.progress=100;job.current_step=p.processing_step;job.completed_at=datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.exception('processing failed'); p=db.query(Project).filter(Project.id==pid).first()
            if p:p.status='failed';p.error_message=str(e);p.processing_step='Failed'
            job=db.query(ProcessingJob).filter(ProcessingJob.id==job_id).first()
            if job:job.status='failed';job.error=str(e);job.current_step='Failed';job.completed_at=datetime.utcnow()
            db.commit()
        finally:db.close()
processor=JobProcessor()
