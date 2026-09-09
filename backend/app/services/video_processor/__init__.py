from .ffmpeg_service import FFmpegNotFoundError, InvalidVideoError, extract_metadata, generate_thumbnail, extract_audio, resolve_executable
from app.services.file_service import validate_video_file, cleanup_temp_files

def check_ffmpeg_available():
    try:
        resolve_executable('ffmpeg')
        resolve_executable('ffprobe')
        return True
    except FFmpegNotFoundError:
        return False
__all__=['FFmpegNotFoundError','InvalidVideoError','check_ffmpeg_available','validate_video_file','extract_metadata','generate_thumbnail','extract_audio','cleanup_temp_files','resolve_executable']
