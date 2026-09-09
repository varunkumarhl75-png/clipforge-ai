from pathlib import Path
import re
import subprocess
from typing import NamedTuple

from app.services.video_processor import resolve_executable


class ShortCandidate(NamedTuple):
    start: float
    duration: float
    hook: str
    score: float
    reason: str


QUALITY_DIMENSIONS = {
    '1080p': (1080, 1920),
    '4k': (2160, 3840),
    '8k': (4320, 7680),
}


def short_dimensions(export_quality='1080p'):
    try:
        return QUALITY_DIMENSIONS[export_quality]
    except KeyError as exc:
        raise ValueError('export_quality must be 1080p, 4k, or 8k') from exc


def _escape_subtitle_filter_path(path):
    """Escape a subtitle path for FFmpeg's filter parser on every OS."""
    return str(Path(path).resolve()).replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")


def create_short(video_path, start, duration, out_path, aspect='9:16', caption_path=None, remove_silence=False, export_quality='1080p'):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    width, height = short_dimensions(export_quality)
    vf = f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}'
    offset_caption_path = None
    if caption_path:
        source_captions = Path(caption_path).read_text(encoding='utf-8')
        timestamp_pattern = re.compile(r'(?P<start>\d{2}:\d{2}:\d{2},\d{3}) --> (?P<end>\d{2}:\d{2}:\d{2},\d{3})')

        def offset_timestamp(match):
            def seconds(value):
                hours, minutes, rest = value.split(':')
                secs, millis = rest.split(',')
                return int(hours) * 3600 + int(minutes) * 60 + int(secs) + int(millis) / 1000

            def format_timestamp(value):
                value = max(0, value)
                hours, remainder = divmod(int(value * 1000), 3600000)
                minutes, remainder = divmod(remainder, 60000)
                secs, millis = divmod(remainder, 1000)
                return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'

            return f'{format_timestamp(seconds(match.group("start")) - start)} --> {format_timestamp(seconds(match.group("end")) - start)}'

        offset_caption_path = Path(out_path).with_suffix('.burnin.srt')
        offset_caption_path.write_text(timestamp_pattern.sub(offset_timestamp, source_captions), encoding='utf-8')
        subtitle_file = _escape_subtitle_filter_path(offset_caption_path)
        # Leave FontName unset so libass can use its standard fallback font.
        vf += f",subtitles='{subtitle_file}':force_style='FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2,MarginV=360'"
    cmd = [resolve_executable('ffmpeg'), '-ss', str(start), '-i', video_path, '-t', str(duration), '-vf', vf]
    if remove_silence:
        cmd += ['-af', 'silenceremove=start_periods=1:start_duration=0.5:start_threshold=-45dB:stop_periods=-1:stop_duration=0.8:stop_threshold=-45dB']
    cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-movflags', '+faststart', '-y', out_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max(180, int(duration * 20) + 60))
    finally:
        if offset_caption_path:
            offset_caption_path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1000:])
    return out_path


def _candidate_for_segment(segment, duration):
    text = ' '.join(str(segment.get('text', '')).split())
    segment_duration = max(0.1, float(segment.get('end', 0)) - float(segment.get('start', 0)))
    clip_duration = min(45.0, max(15.0, round(segment_duration + 20, 1)), duration)
    start = max(0.0, min(float(segment.get('start', 0)) - 5.0, duration - clip_duration))
    words = text.split()
    question_bonus = 0.12 if '?' in text else 0
    intensity_bonus = 0.12 if any(word.lower() in {'how', 'why', 'secret', 'mistake', 'never', 'best', 'must'} for word in words) else 0
    context_score = min(0.25, len(words) / 40)
    completeness = 0.18 if len(words) >= 7 else 0.08
    duration_score = 0.18 if 20 <= clip_duration <= 45 else 0.1
    score = min(1.0, round(0.2 + question_bonus + intensity_bonus + context_score + completeness + duration_score, 3))
    reason = f'hook signals {question_bonus + intensity_bonus:.2f}; context density {context_score:.2f}; completeness {completeness:.2f}; duration fit {duration_score:.2f}'
    return ShortCandidate(start, clip_duration, text or 'Key moment from your video', score, reason)


def suggest_windows(duration, segments, max_shorts=10, block_seconds=600, min_score=0.45):
    """Select strong, non-clustered moments across the full transcript timeline."""
    if duration <= 0:
        return []
    candidates = [_candidate_for_segment(segment, duration) for segment in segments]
    candidates = [candidate for candidate in candidates if candidate.score >= min_score]
    if not candidates:
        return [ShortCandidate(0, min(45.0, duration), 'Best moment from your video', 0.45, 'Fallback candidate because no transcript moment reached the score threshold')]
    by_block = {}
    for candidate in candidates:
        block = int(candidate.start // block_seconds)
        if block not in by_block or candidate.score > by_block[block].score:
            by_block[block] = candidate
    # Keep the first pass chronological so the ten-clip default represents the
    # whole long-form video instead of returning ten moments from the opening.
    selected = sorted(by_block.values(), key=lambda candidate: candidate.start)
    selected = selected[:max_shorts]
    for candidate in candidates:
        if len(selected) >= max_shorts:
            break
        if all(abs(candidate.start - chosen.start) >= 30 for chosen in selected):
            selected.append(candidate)
    return sorted(selected[:max_shorts], key=lambda candidate: candidate.score, reverse=True)
