from pydantic import BaseModel,Field,field_validator,ConfigDict
from typing import Optional,Dict,Any
from datetime import datetime
from urllib.parse import urlparse
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source_type: str = 'upload'
    source_url: Optional[str] = None

    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls,value):
        if value not in {'upload','youtube_url'}:
            raise ValueError('source_type must be upload or youtube_url')
        return value
    @field_validator('source_url')
    @classmethod
    def validate_source_url(cls,value):
        if value is not None:
            parsed=urlparse(value)
            if parsed.scheme not in {'http','https'} or parsed.netloc not in {'youtube.com','www.youtube.com','m.youtube.com','youtu.be','www.youtu.be'}:
                raise ValueError('source_url must be a YouTube URL')
        return value
class ProjectResponse(BaseModel):
    id:str;name:str;source_type:str;source_url:Optional[str]=None;original_filename:Optional[str]=None;status:str;created_at:datetime;updated_at:datetime
    video_file_path:Optional[str]=None;duration:Optional[float]=None;width:Optional[int]=None;height:Optional[int]=None;fps:Optional[float]=None;video_codec:Optional[str]=None;audio_codec:Optional[str]=None;bitrate:Optional[str]=None;file_size:Optional[int]=None;has_audio:bool=False;thumbnail_path:Optional[str]=None;audio_path:Optional[str]=None;error_message:Optional[str]=None;processing_progress:int=0;processing_step:str='Waiting'
    model_config = ConfigDict(from_attributes=True)
class VideoUploadResponse(BaseModel): project_id:str;filename:str;file_path:str;status:str
class YouTubeImportRequest(BaseModel):
    url:str
    @field_validator('url')
    @classmethod
    def validate_url(cls,value):
        parsed=urlparse(value)
        if parsed.scheme not in {'http','https'} or parsed.netloc.lower() not in {'youtube.com','www.youtube.com','m.youtube.com','youtu.be','www.youtu.be'}:
            raise ValueError('Only YouTube URLs are supported')
        return value
class ShortsRequest(BaseModel):
    count:int=Field(default=10,ge=1,le=50)
    max_shorts: Optional[int] = Field(default=None, ge=1, le=50)
    limit: Optional[int] = Field(default=None, ge=1, le=50)
    burn_captions: bool = False
    remove_silence: bool = False
    export_quality: str = '1080p'

    @field_validator('export_quality')
    @classmethod
    def validate_export_quality(cls, value):
        if value not in {'1080p', '4k', '8k'}:
            raise ValueError('export_quality must be 1080p, 4k, or 8k')
        return value

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    aspect_ratio: str = '16:9'

    @field_validator('aspect_ratio')
    @classmethod
    def validate_aspect_ratio(cls, value):
        if value not in {'16:9', '9:16'}:
            raise ValueError('aspect_ratio must be 16:9 or 9:16')
        return value

class ThumbnailGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)

class EditRequest(BaseModel):
    spec: Dict[str, Any]
    export_quality: str = '1080p'

    @field_validator('export_quality')
    @classmethod
    def validate_export_quality(cls, value):
        if value not in {'1080p', '4k', '8k'}:
            raise ValueError('export_quality must be 1080p, 4k, or 8k')
        return value
class ChannelRequest(BaseModel): channel_name:str='My Channel';youtube_channel_id:Optional[str]=None

class ChapterResponse(BaseModel):
    id: int
    project_id: str
    start_time: float
    title: str
    model_config = ConfigDict(from_attributes=True)

class ContentPackageResponse(BaseModel):
    id: int
    project_id: str
    title_suggestions: list[str]
    description: str
    hashtags: list[str]
    tags: list[str]
    hooks: list[str]
    thumbnail_text_suggestions: list[str]
    provider: str
    status: str
    error_message: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class YouTubePublishRequest(BaseModel):
    access_token:str
    title:str=Field(...,min_length=1,max_length=100)
    description:str=''
    privacy_status:str='private'
    tags:list[str]=[]
