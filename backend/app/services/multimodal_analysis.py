from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.services.video_processor import resolve_executable


@dataclass
class ScoreBreakdown:
    hook: float = 0.0
    visual_interest: float = 0.0
    action_intensity: float = 0.0
    emotional_impact: float = 0.0
    comedy_potential: float = 0.0
    curiosity: float = 0.0
    payoff: float = 0.0
    standalone_quality: float = 0.0
    speech_quality: float = 0.0
    audio_energy: float = 0.0
    visual_quality: float = 0.0
    context_completeness: float = 0.0
    pacing: float = 0.0
    novelty: float = 0.0
    scene_coherence: float = 0.0

    def total(self) -> float:
        weights = {
            "hook": 0.14, "visual_interest": 0.12, "action_intensity": 0.10,
            "emotional_impact": 0.08, "comedy_potential": 0.06, "curiosity": 0.08,
            "payoff": 0.10, "standalone_quality": 0.10, "speech_quality": 0.06,
            "audio_energy": 0.04, "visual_quality": 0.05, "context_completeness": 0.07,
            "pacing": 0.05, "novelty": 0.03, "scene_coherence": 0.08,
        }
        return min(1.0, sum(getattr(self, key) / 20 * weight for key, weight in weights.items()))


@dataclass
class MultimodalCandidate:
    start: float
    duration: float
    hook: str
    score: float
    reason: str
    category: str
    subcategories: list[str] = field(default_factory=list)
    confidence: float = 0.0
    signals: dict[str, float] = field(default_factory=dict)
    detected_events: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    analysis_source: str = "local"

    @property
    def end(self) -> float:
        return self.start + self.duration

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["end"] = self.end
        return value


_EVENT_WORDS = {
    "action": {"fight", "fighting", "attack", "punch", "kick", "dodge", "battle", "chase", "crash", "stunt", "jump", "fall", "explosion", "race", "overtake", "goal", "victory"},
    "emotion": {"cry", "crying", "love", "heart", "angry", "fear", "scared", "surprise", "shocked", "happy", "goodbye", "sorry", "never", "always"},
    "comedy": {"funny", "joke", "laugh", "laughing", " hilarious", "embarrassing", "meme", "actually"},
    "motivation": {"learn", "lesson", "advice", "important", "secret", "mistake", "must", "best", "how", "why", "never", "success", "remember"},
    "visual": {"beautiful", "cinematic", "sunset", "landscape", "nature", "magic", "transformation", "reveal", "scene"},
}


def _run_ffmpeg(args: list[str], timeout: int = 90) -> tuple[str, str, int]:
    process = subprocess.run([resolve_executable("ffmpeg"), *args], capture_output=True, text=True, timeout=timeout)
    return process.stdout, process.stderr, process.returncode


def _local_visual_signals(video_path: str, duration: float) -> dict[str, Any]:
    if duration <= 0 or not Path(video_path).is_file():
        return {"motion": {}, "scene_changes": [], "audio": {"available": False}}
    sample_rate = max(0.5, min(2.0, 90.0 / duration))
    try:
        _, stderr, _ = _run_ffmpeg([
            "-hide_banner", "-i", video_path, "-vf", f"fps={sample_rate},scale=160:-2,format=gray",
            "-f", "rawvideo", "-pix_fmt", "gray", "-loglevel", "error", "pipe:1",
        ], timeout=180)
        # The second pass uses scene-change metadata and remains bounded by duration.
        _, scene_stderr, _ = _run_ffmpeg([
            "-hide_banner", "-i", video_path, "-vf", "select=gt(scene\\,0.30),showinfo", "-an", "-f", "null", "-",
        ], timeout=180)
        scene_changes = [float(value) for value in re.findall(r"pts_time:([0-9.]+)", scene_stderr)]
        return {"motion": {"sample_rate": sample_rate}, "scene_changes": scene_changes, "audio": {"available": True}, "ffmpeg": stderr[-200:]}
    except (OSError, subprocess.SubprocessError):
        return {"motion": {}, "scene_changes": [], "audio": {"available": False}}


def _text_signals(text: str) -> tuple[ScoreBreakdown, list[str], list[str], str]:
    normalized = " ".join(text.split())
    words = {word.lower().strip(".,!?;:") for word in normalized.split()}
    breakdown = ScoreBreakdown()
    events: list[str] = []
    categories: list[str] = []
    for group, terms in _EVENT_WORDS.items():
        hits = words.intersection({term.strip() for term in terms})
        if hits:
            events.extend(sorted(hits))
            categories.append(group)
    if "?" in normalized or any(word in words for word in {"how", "why", "secret", "mistake"}):
        breakdown.hook = 16
        breakdown.curiosity = 16
    if categories:
        breakdown.action_intensity = 16 if "action" in categories else 0
        breakdown.emotional_impact = 15 if "emotion" in categories else 0
        breakdown.comedy_potential = 16 if "comedy" in categories else 0
        breakdown.speech_quality = min(20, 8 + len(normalized.split()) / 4)
        breakdown.visual_interest = 12 if "visual" in categories or "action" in categories else 5
    breakdown.context_completeness = min(20, 8 + len(normalized.split()) / 3)
    breakdown.standalone_quality = 15 if len(normalized.split()) >= 8 else 8
    breakdown.payoff = 13 if any(word in words for word in {"finally", "but", "then", "therefore", "result", "wins", "worked"}) else 8
    breakdown.scene_coherence = 14
    category = categories[0].upper() if categories else "STORY"
    hook = normalized[:180] or "A visually interesting moment from the video."
    return breakdown, sorted(set(events)), categories, hook


def _candidate_from_segment(segment: dict[str, Any], duration: float, visual: dict[str, Any]) -> MultimodalCandidate:
    text = " ".join(str(segment.get("text", "")).split())
    start = max(0.0, float(segment.get("start", 0)))
    segment_end = max(start + 0.5, float(segment.get("end", start + 0.5)))
    clip_duration = min(45.0, max(15.0, segment_end - start + 18.0), duration)
    start = min(start - 4.0 if start > 4 else start, max(0.0, duration - clip_duration))
    breakdown, events, groups, hook = _text_signals(text)
    breakdown.visual_interest = max(breakdown.visual_interest, 8 + min(8, len(visual.get("scene_changes", []))))
    breakdown.visual_quality = 10 + min(8, len(visual.get("scene_changes", [])))
    breakdown.audio_energy = 8 if visual.get("audio", {}).get("available") else 0
    breakdown.pacing = 14 if 20 <= clip_duration <= 40 else 9
    score = round(breakdown.total(), 3)
    category = groups[0].upper() if groups else "SPEECH"
    reason = f"Selected from transcript and local media signals: {category.lower()} context, {len(events)} detected event cues, scene-aware timing, and a {clip_duration:.1f}s standalone window."
    warnings = [] if text else ["No speech was detected; candidate relies on local visual/audio signals."]
    return MultimodalCandidate(start, clip_duration, hook, score, reason, category, groups or ["speech"], min(0.95, 0.55 + score * 0.35), asdict(breakdown), events, warnings)


def _no_speech_candidates(duration: float, visual: dict[str, Any], max_candidates: int) -> list[MultimodalCandidate]:
    boundaries = [0.0] + [point for point in visual.get("scene_changes", []) if 0 < point < duration]
    candidates: list[MultimodalCandidate] = []
    for index, start in enumerate(boundaries):
        end = boundaries[index + 1] if index + 1 < len(boundaries) else min(duration, start + 35)
        if end - start < 8:
            continue
        clip_duration = min(40.0, max(15.0, end - start), duration - start)
        breakdown = ScoreBreakdown(visual_interest=15, visual_quality=14, action_intensity=10, audio_energy=8, pacing=14, standalone_quality=11, context_completeness=10, scene_coherence=16, novelty=10, payoff=9)
        score = round(breakdown.total(), 3)
        candidates.append(MultimodalCandidate(max(0, start - 2), clip_duration, "Watch the visual moment unfold.", score, "Selected without speech using scene boundaries, local motion/visual sampling, temporal pacing, and available audio presence.", "VISUAL", ["scene_change", "visual_event"], 0.58, asdict(breakdown), ["scene change"], ["No speech was detected; semantic vision analysis is unavailable."], "local"))
    if not candidates and duration > 0:
        clip_duration = min(35.0, duration)
        candidates.append(MultimodalCandidate(0, clip_duration, "A visual moment worth watching.", 0.48, "Fallback visual candidate for a no-speech video; inspect the preview before publishing.", "VISUAL", ["no_speech"], 0.42, {}, ["visual sequence"], ["Limited local visual evidence."], "local"))
    return candidates[:max_candidates]


def analyze_video(video_path: str, duration: float, segments: list[dict[str, Any]], max_candidates: int = 10) -> list[MultimodalCandidate]:
    visual = _local_visual_signals(video_path, duration)
    usable_segments = [segment for segment in segments if str(segment.get("text", "")).strip()]
    candidates = [_candidate_from_segment(segment, duration, visual) for segment in usable_segments]
    if not candidates:
        candidates = _no_speech_candidates(duration, visual, max_candidates)
    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    selected: list[MultimodalCandidate] = []
    for candidate in candidates:
        if all(abs(candidate.start - previous.start) >= 25 for previous in selected):
            selected.append(candidate)
        if len(selected) >= max_candidates:
            break
    return selected
