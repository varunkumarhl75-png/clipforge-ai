from html import escape
from pathlib import Path
import subprocess
import uuid

from app.core import settings
from app.services.video_processor import resolve_executable


def _dimensions(aspect_ratio: str) -> tuple[int, int]:
    return (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)


def generate_image(prompt: str, aspect_ratio: str = "16:9") -> str:
    width, height = _dimensions(aspect_ratio)
    output = Path(settings.PROCESSED_DIR) / "ai" / "images" / f"{uuid.uuid4()}.svg"
    output.parent.mkdir(parents=True, exist_ok=True)
    words = escape(" ".join(prompt.split())[:180])
    output.write_text(
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#100b24"/><stop offset=".55" stop-color="#31205e"/><stop offset="1" stop-color="#a46120"/></linearGradient></defs>
<rect width="100%" height="100%" fill="url(#bg)"/><circle cx="{width * .78}" cy="{height * .2}" r="{min(width, height) * .16}" fill="#fbbf24" opacity=".22"/>
<text x="8%" y="78%" fill="#fff" font-family="Arial,sans-serif" font-size="{max(28, width // 28)}" font-weight="700">NYXARCLIP AI</text>
<text x="8%" y="84%" fill="#fde68a" font-family="Arial,sans-serif" font-size="{max(18, width // 52)}">{words}</text></svg>''',
        encoding="utf-8",
    )
    return str(output)


def generate_video(prompt: str, aspect_ratio: str = "9:16") -> str:
    width, height = _dimensions(aspect_ratio)
    output = Path(settings.PROCESSED_DIR) / "ai" / "videos" / f"{uuid.uuid4()}.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        resolve_executable("ffmpeg"), "-f", "lavfi", "-i",
        f"color=c=0x17112b:s={width}x{height}:r=30:d=5",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-shortest", "-movflags", "+faststart", "-y", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(result.stderr[-1200:] or "Video generation failed")
    return str(output)