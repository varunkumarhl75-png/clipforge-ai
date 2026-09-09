"""
AI services for ClipForge AI.

Currently uses faster-whisper locally for transcription.
No external AI API key is required.
"""

from typing import Any
import re
from app.core import settings


def transcribe_audio(
    audio_path: str,
    model_name: str = "small",
) -> dict[str, Any]:
    """
    Transcribe an audio file using faster-whisper.
    """

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. "
            "Run: pip install faster-whisper"
        ) from exc

    print(f"[Whisper] Loading model: {model_name}")
    print(f"[Whisper] Input: {audio_path}")

    model = WhisperModel(
        model_name,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )

    print("[Whisper] Starting transcription...")

    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
    )

    output_segments: list[dict[str, Any]] = []

    for segment in segments:
        text = segment.text.strip()

        if not text:
            continue

        output_segments.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
            }
        )

    language = getattr(info, "language", "en") or "en"

    full_text = " ".join(
        segment["text"]
        for segment in output_segments
    )

    print(
        f"[Whisper] Language: {language} | "
        f"Segments: {len(output_segments)} | "
        f"Characters: {len(full_text)}"
    )

    return {
        "language": language,
        "segments": output_segments,
        "text": full_text,
    }


def repurpose(
    text: str,
    count: int = 5,
) -> list[dict[str, Any]]:
    """
    Temporary deterministic content-repurposing helper.
    """

    words = re.findall(r"\b[\w'-]+\b", text)

    clean = " ".join(words)

    chunks = re.split(
        r"(?<=[.!?])\s+",
        clean,
    )

    seed = (
        " ".join(chunks[:2])[:180]
        if chunks
        else clean[:180]
    )

    topic = (
        " ".join(words[:8])
        if words
        else "your video"
    )

    ideas = []

    templates = [
        (
            "The 30-second lesson",
            "Here is the key idea in under 30 seconds.",
        ),
        (
            "3 things you should know",
            "These are the most important takeaways.",
        ),
        (
            "The part nobody tells you",
            "This is the detail worth remembering.",
        ),
        (
            "Quick breakdown",
            "Let's break the main idea down simply.",
        ),
        (
            "Watch this before you start",
            "Save this tip for later.",
        ),
    ]

    for i in range(min(count, len(templates))):
        title, hook = templates[i]

        ideas.append(
            {
                "title": f"{title}: {topic[:45]}",
                "hook": hook,
                "caption": seed,
                "hashtags": [
                    "#ClipForge",
                    "#Shorts",
                    "#CreatorTips",
                ],
            }
        )

    return ideas