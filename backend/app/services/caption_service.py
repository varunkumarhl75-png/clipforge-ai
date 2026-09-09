from pathlib import Path
from typing import Iterable


def format_srt_timestamp(seconds: float) -> str:
    """
    Convert seconds into SRT timestamp format.

    Example:
    7.5 -> 00:00:07,500
    """

    milliseconds = max(0, int(round(seconds * 1000)))

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    secs = milliseconds // 1_000
    milliseconds %= 1_000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


def format_vtt_timestamp(seconds: float) -> str:
    """
    Convert seconds into WebVTT timestamp format.

    Example:
    7.5 -> 00:00:07.500
    """

    milliseconds = max(0, int(round(seconds * 1000)))

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    secs = milliseconds // 1_000
    milliseconds %= 1_000

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}."
        f"{milliseconds:03d}"
    )


def write_captions(
    project_id: str,
    segments: Iterable[dict],
    output_dir: Path,
):
    """
    Generate SRT and VTT files from transcript segments.

    Each segment must contain:

        start
        end
        text
    """

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    srt_path = (
        output_dir
        / f"{project_id}.srt"
    )

    vtt_path = (
        output_dir
        / f"{project_id}.vtt"
    )

    normalized_segments = []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = max(0.0, float(segment.get("start", 0)))
        end = max(start, float(segment.get("end", start)))
        normalized_segments.append({"start": start, "end": end, "text": text})

    # --------------------------------------------------------
    # SRT
    # --------------------------------------------------------

    srt_lines = []

    for index, segment in enumerate(
        normalized_segments,
        start=1
    ):
        srt_lines.extend([
            str(index),
            f"{format_srt_timestamp(segment['start'])} --> "
            f"{format_srt_timestamp(segment['end'])}",
            segment["text"],
            "",
        ])

    srt_path.write_text(
        "\n".join(srt_lines),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # WEBVTT
    # --------------------------------------------------------

    vtt_lines = [
        "WEBVTT",
        ""
    ]

    for segment in normalized_segments:
        vtt_lines.extend([
            f"{format_vtt_timestamp(segment['start'])} --> "
            f"{format_vtt_timestamp(segment['end'])}",
            segment["text"],
            "",
        ])

    vtt_path.write_text(
        "\n".join(vtt_lines),
        encoding="utf-8"
    )

    return (
        str(srt_path),
        str(vtt_path)
    )