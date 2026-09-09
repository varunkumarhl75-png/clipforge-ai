from sqlalchemy import Column, String, Integer, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db.database import Base

class ProjectStatusEnum(str, PyEnum):
    PENDING='pending'; QUEUED='queued'; PROCESSING='processing'; COMPLETED='completed'; FAILED='failed'
class SourceTypeEnum(str, PyEnum):
    UPLOAD='upload'; YOUTUBE_URL='youtube_url'

class Project(Base):
    __tablename__='projects'
    id=Column(String,primary_key=True,index=True); name=Column(String,nullable=False)
    source_type=Column(String,default='upload'); source_url=Column(String,nullable=True); original_filename=Column(String,nullable=True)
    status=Column(String,default='pending'); video_file_path=Column(String,nullable=True); thumbnail_path=Column(String,nullable=True); audio_path=Column(String,nullable=True)
    duration=Column(Float,nullable=True); width=Column(Integer,nullable=True); height=Column(Integer,nullable=True); fps=Column(Float,nullable=True)
    video_codec=Column(String,nullable=True); audio_codec=Column(String,nullable=True); bitrate=Column(String,nullable=True); file_size=Column(Integer,nullable=True); has_audio=Column(Boolean,default=False)
    error_message=Column(Text,nullable=True); processing_progress=Column(Integer,default=0); processing_step=Column(String,default='Waiting')
    created_at=Column(DateTime,server_default=func.now()); updated_at=Column(DateTime,server_default=func.now(),onupdate=func.now())

class Transcript(Base):
    __tablename__='transcripts'
    id=Column(Integer,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True); language=Column(String,default='en'); full_text=Column(Text,default=''); status=Column(String,default='pending'); created_at=Column(DateTime,server_default=func.now())
class TranscriptSegment(Base):
    __tablename__='transcript_segments'
    id=Column(Integer,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True); start=Column(Float); end=Column(Float); text=Column(Text); speaker=Column(String,nullable=True)
class Caption(Base):
    __tablename__='captions'
    id=Column(Integer,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True); style=Column(String,default='bold'); srt_path=Column(String); vtt_path=Column(String); status=Column(String,default='ready')
class Short(Base):
    __tablename__='shorts'
    id=Column(String,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True); title=Column(String); start=Column(Float); duration=Column(Float); video_path=Column(String,nullable=True); caption_path=Column(String,nullable=True); hook=Column(String,nullable=True); score=Column(Float,nullable=True); reason=Column(Text,nullable=True); category=Column(String,nullable=True); subcategories=Column(JSON,nullable=True); confidence=Column(Float,nullable=True); signals=Column(JSON,nullable=True); detected_events=Column(JSON,nullable=True); warnings=Column(JSON,nullable=True); analysis_source=Column(String,default='local'); status=Column(String,default='queued')
class EditJob(Base):
    __tablename__='edit_jobs'
    id=Column(String,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True); spec_json=Column(Text); output_path=Column(String,nullable=True); status=Column(String,default='queued'); error_message=Column(Text,nullable=True); created_at=Column(DateTime,server_default=func.now())
class ChannelSetting(Base):
    __tablename__='channel_settings'
    id=Column(Integer,primary_key=True); channel_name=Column(String,default='My Channel'); youtube_connected=Column(Boolean,default=False); youtube_channel_id=Column(String,nullable=True); youtube_access_token=Column(Text,nullable=True); created_at=Column(DateTime,server_default=func.now())

class Chapter(Base):
    __tablename__='chapters'
    id=Column(Integer,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True,nullable=False); start_time=Column(Float,nullable=False); title=Column(String,nullable=False)

class ContentPackage(Base):
    __tablename__='content_packages'
    id=Column(Integer,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True,nullable=False); title_suggestions=Column(JSON,default=list); description=Column(Text,default=''); hashtags=Column(JSON,default=list); tags=Column(JSON,default=list); hooks=Column(JSON,default=list); thumbnail_text_suggestions=Column(JSON,default=list); provider=Column(String,default='none'); status=Column(String,default='not_configured'); error_message=Column(Text,nullable=True); created_at=Column(DateTime,server_default=func.now())

class ProcessingJob(Base):
    __tablename__='processing_jobs'
    id=Column(String,primary_key=True); project_id=Column(String,ForeignKey('projects.id',ondelete='CASCADE'),index=True,nullable=False); status=Column(String,default='queued'); progress=Column(Integer,default=0); current_step=Column(String,default='Queued'); error=Column(Text,nullable=True); created_at=Column(DateTime,server_default=func.now()); started_at=Column(DateTime,nullable=True); completed_at=Column(DateTime,nullable=True)
