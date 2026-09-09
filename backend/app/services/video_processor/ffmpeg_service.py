import shutil
import subprocess,json,logging,os
from pathlib import Path
from typing import Optional
from app.core import settings
logger=logging.getLogger(__name__)
class InvalidVideoError(Exception):pass
class FFmpegNotFoundError(Exception):pass

def _resolve_executable(configured_path: str, executable_name: str) -> str:
    """Resolve an explicitly configured or PATH-discoverable media executable."""
    configured = (configured_path or '').strip()
    candidates = [configured] if configured else []
    if configured and not Path(configured).is_absolute():
        candidates.append(str(Path.cwd() / configured))
    candidates.append(executable_name)

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        candidate_path = Path(candidate)
        if candidate_path.is_file():
            return str(candidate_path)

    for root in filter(None, os.environ.get('PATH', '').split(os.pathsep)):
        root_path = Path(root)
        for suffix in ('', '.exe'):
            candidate_path = root_path / f'{executable_name}{suffix}'
            if candidate_path.is_file():
                return str(candidate_path)

    raise FFmpegNotFoundError(
        f'{executable_name} was not found. Set {"FFMPEG_PATH" if executable_name == "ffmpeg" else "FFPROBE_PATH"} '
        'to the executable path or add its directory to PATH.'
    )

def _executable_path(executable_name: str) -> str:
    configured = settings.FFMPEG_PATH if executable_name == 'ffmpeg' else settings.FFPROBE_PATH
    return _resolve_executable(configured, executable_name)

def resolve_executable(executable_name: str) -> str:
    return _executable_path(executable_name)

def _run_command(cmd,timeout=300):
    try:
        cmd = list(cmd)
        if cmd and Path(str(cmd[0])).name.lower().split('.')[0] in {'ffmpeg', 'ffprobe'}:
            cmd[0] = _executable_path(Path(str(cmd[0])).name.lower().split('.')[0])
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    except FileNotFoundError as e:raise FFmpegNotFoundError('FFmpeg/FFprobe is not installed or not on PATH') from e
    return r.stdout,r.stderr,r.returncode

def extract_metadata(video_path):
    if not Path(video_path).exists():raise InvalidVideoError('Video file not found')
    cmd=['ffprobe','-v','error','-print_format','json','-show_format','-show_streams',video_path]
    try:
        stdout,stderr,code=_run_command(cmd,60)
    except FFmpegNotFoundError:
        raise
    except Exception as exc:
        raise InvalidVideoError(str(exc)) from exc
    if code!=0:raise InvalidVideoError(stderr[-1000:] or 'Unable to read video')
    try:data=json.loads(stdout)
    except json.JSONDecodeError as e:raise InvalidVideoError('Invalid ffprobe response') from e
    streams=data.get('streams',[]);v=next((s for s in streams if s.get('codec_type')=='video'),None);a=next((s for s in streams if s.get('codec_type')=='audio'),None)
    if not v:raise InvalidVideoError('No video stream found')
    fps=v.get('r_frame_rate','0/1');
    try:fpsv=round(float(fps.split('/')[0])/float(fps.split('/')[1]),3) if '/' in fps else float(fps)
    except:fpsv=0
    fmt=data.get('format',{});return {'duration':float(fmt.get('duration',0) or 0),'width':v.get('width'),'height':v.get('height'),'fps':fpsv,'video_codec':v.get('codec_name'),'audio_codec':a.get('codec_name') if a else None,'bitrate':fmt.get('bit_rate') or v.get('bit_rate'),'file_size':int(fmt.get('size',0) or 0),'has_audio':a is not None}

def generate_thumbnail(video_path,output_path,timestamp=None):
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    if timestamp is None:timestamp=extract_metadata(video_path)['duration']*0.1
    _,err,code=_run_command(['ffmpeg','-ss',str(max(0,timestamp)),'-i',video_path,'-frames:v','1','-vf','scale=640:-2','-y',output_path],60);return code==0 and Path(output_path).exists()

def extract_audio(video_path,output_path,audio_codec='pcm_s16le'):
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    if not extract_metadata(video_path).get('has_audio'):return False
    _,err,code=_run_command(['ffmpeg','-i',video_path,'-vn','-acodec',audio_codec,'-ar','16000','-ac','1','-y',output_path],300);return code==0 and Path(output_path).exists()

class FFmpegService:
    """Compatibility facade for the media-processing helpers."""

    def check_ffmpeg_available(self) -> bool:
        try:
            _run_command(['ffmpeg', '-version'], 15)
            _run_command(['ffprobe', '-version'], 15)
            return True
        except FFmpegNotFoundError:
            return False

    def validate_video_file(self, video_path: str) -> bool:
        try:
            extract_metadata(video_path)
        except FFmpegNotFoundError:
            raise
        except Exception as exc:
            if isinstance(exc, InvalidVideoError):
                raise
            raise InvalidVideoError(str(exc)) from exc
        return True

    def extract_metadata(self, video_path: str):
        return extract_metadata(video_path)

    def generate_thumbnail(self, video_path: str, output_path: str, timestamp=None):
        if timestamp is None:
            timestamp = 0
        try:
            subprocess.run(
                [_executable_path('ffmpeg'), '-ss', str(max(0, timestamp)), '-i', video_path,
                 '-frames:v', '1', '-vf', 'scale=640:-2', '-y', output_path],
                capture_output=True, text=True, timeout=60, check=True,
            )
            return True
        except FileNotFoundError as exc:
            raise FFmpegNotFoundError(str(exc)) from exc
        except subprocess.CalledProcessError as exc:
            raise InvalidVideoError(exc.stderr or 'Unable to generate thumbnail') from exc

    def extract_audio(self, video_path: str, output_path: str, audio_codec='pcm_s16le'):
        try:
            subprocess.run(
                [_executable_path('ffmpeg'), '-i', video_path, '-vn', '-acodec', audio_codec,
                 '-ar', '16000', '-ac', '1', '-y', output_path],
                capture_output=True, text=True, timeout=300, check=True,
            )
            return True
        except FileNotFoundError as exc:
            raise FFmpegNotFoundError(str(exc)) from exc
        except subprocess.CalledProcessError as exc:
            raise InvalidVideoError(exc.stderr or 'Unable to extract audio') from exc

    def cleanup_temp_files(self, *paths: str):
        for path in paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                logger.warning('Unable to remove temporary file %s', path)
