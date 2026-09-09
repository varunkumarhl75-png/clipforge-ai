from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    APP_NAME:str='NyxarClip AI'; DEBUG:bool=True; DEMO_MODE:bool=False
    DATABASE_URL:str='sqlite:///./app/db/clipforge.db'
    UPLOAD_MAX_SIZE:int=5_000_000_000; UPLOAD_DIR:str='storage/uploads'; PROCESSED_DIR:str='storage/processed'; TEMPORARY_DIR:str='storage/temporary'
    FFMPEG_PATH:str='ffmpeg'; FFPROBE_PATH:str='ffprobe'; NEXT_PUBLIC_API_URL:str='http://localhost:8000'
    YOUTUBE_COOKIES_FILE:str=''; WHISPER_MODEL:str='small'; WHISPER_DEVICE:str='cpu'; WHISPER_COMPUTE_TYPE:str='int8'; OPENAI_API_KEY:str=''; OPENAI_MODEL:str='gpt-4o-mini'; AI_PROVIDER:str='gemini'; GEMINI_API_KEY:str=''; GEMINI_MODEL:str='gemini-2.5-flash'; GEMINI_IMAGE_MODEL:str=''; MAX_SHORT_CANDIDATES:int=10; MIN_SHORT_DURATION:float=15.0; MAX_SHORT_DURATION:float=45.0; YOUTUBE_CLIENT_ID:str=''; YOUTUBE_CLIENT_SECRET:str=''
    model_config=SettingsConfigDict(env_file='.env',case_sensitive=True,extra='ignore')
settings=Settings()
