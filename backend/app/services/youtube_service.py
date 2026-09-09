from pathlib import Path

from app.services.video_processor import resolve_executable

def download_youtube(url:str, out_dir:str):
    try:
        import yt_dlp
    except ImportError as e:
        raise RuntimeError('yt-dlp is not installed. Run: pip install yt-dlp') from e
    Path(out_dir).mkdir(parents=True,exist_ok=True)
    output_dir = Path(out_dir)
    opts={'format':'bv*+ba/b','merge_output_format':'mp4','outtmpl':str(output_dir/'youtube.%(ext)s'),'noplaylist':True,'quiet':True}
    ffmpeg_path = resolve_executable('ffmpeg')
    opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
    from app.core import settings
    if settings.YOUTUBE_COOKIES_FILE: opts['cookiefile']=settings.YOUTUBE_COOKIES_FILE
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(url,download=True)
        path=Path(ydl.prepare_filename(info))
        candidates = [path.with_suffix('.mp4'), output_dir / 'youtube.mp4']
        path = next((candidate for candidate in candidates if candidate.is_file()), path)
        if not path.is_file():
            merged = sorted(output_dir.glob('youtube.*'), key=lambda item: item.stat().st_mtime, reverse=True)
            if merged:
                path = merged[0]
        return str(path), info
