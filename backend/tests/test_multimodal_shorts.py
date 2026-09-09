import pytest
from app.services.multimodal_analysis import (
    ScoreBreakdown,
    MultimodalCandidate,
    _text_signals,
    _candidate_from_segment,
    _no_speech_candidates,
    analyze_video,
)


class TestScoreBreakdown:
    def test_score_total_is_normalized(self):
        breakdown = ScoreBreakdown(hook=20, visual_interest=20, action_intensity=20)
        total = breakdown.total()
        assert 0 <= total <= 1.0

    def test_empty_breakdown_has_zero_total(self):
        breakdown = ScoreBreakdown()
        assert breakdown.total() == 0.0

    def test_weighted_averaging(self):
        breakdown = ScoreBreakdown(payoff=20, standalone_quality=20)
        total = breakdown.total()
        assert 0 < total < 0.3


class TestMultimodalCandidate:
    def test_candidate_end_time_calculation(self):
        candidate = MultimodalCandidate(start=10.0, duration=5.0, hook="test", score=0.5, reason="test reason", category="ACTION")
        assert candidate.end == 15.0

    def test_candidate_as_dict_includes_end(self):
        candidate = MultimodalCandidate(start=10.0, duration=5.0, hook="test", score=0.5, reason="test", category="ACTION")
        d = candidate.as_dict()
        assert d["end"] == 15.0
        assert d["start"] == 10.0
        assert d["category"] == "ACTION"


class TestTextSignals:
    def test_question_detection(self):
        breakdown, events, groups, hook = _text_signals("What is the secret to success?")
        assert breakdown.hook > 10
        assert breakdown.curiosity > 10
        assert "story" not in groups or "motivation" in groups

    def test_action_word_detection(self):
        breakdown, events, groups, hook = _text_signals("The fighter dodges the attack and lands a counter punch.")
        assert "action" in groups
        assert any(event in {"dodge", "counter", "punch", "attack"} for event in events)

    def test_emotional_language(self):
        breakdown, events, groups, hook = _text_signals("I was crying because I thought I lost him forever.")
        assert "emotion" in groups
        assert breakdown.emotional_impact > 10

    def test_motivational_content(self):
        breakdown, events, groups, hook = _text_signals("Here is the most important lesson you must learn.")
        assert "motivation" in groups or breakdown.hook > 10

    def test_empty_text_returns_minimal_signals(self):
        breakdown, events, groups, hook = _text_signals("")
        assert len(events) == 0
        assert len(groups) == 0
        assert breakdown.total() >= 0

    def test_long_text_improves_context_score(self):
        short_text = "Act now."
        long_text = "This is a comprehensive explanation of why you should act immediately because the opportunity will not remain available indefinitely and the consequences of waiting are quite significant."
        _, _, _, _ = _text_signals(short_text)
        breakdown_long, _, _, _ = _text_signals(long_text)
        assert breakdown_long.context_completeness > 8


class TestCandidateGeneration:
    def test_candidate_from_speech_segment(self):
        segment = {"start": 10.0, "end": 18.0, "text": "This is a challenging situation that requires immediate action."}
        visual = {"scene_changes": [], "audio": {"available": True}}
        candidate = _candidate_from_segment(segment, 120.0, visual)
        
        assert candidate.start >= 0
        assert candidate.duration >= 15.0
        assert candidate.duration <= 45.0
        assert candidate.score > 0
        assert len(candidate.hook) > 0
        assert candidate.category in ["ACTION", "MOTIVATION", "SPEECH", "STORY"]

    def test_candidate_respects_video_bounds(self):
        segment = {"start": 1.0, "end": 3.0, "text": "Quick moment."}
        visual = {"scene_changes": [], "audio": {"available": False}}
        candidate = _candidate_from_segment(segment, 10.0, visual)
        
        assert candidate.start >= 0
        assert candidate.end <= 10.0

    def test_silent_segment_includes_warning(self):
        segment = {"start": 10.0, "end": 12.0, "text": ""}
        visual = {"scene_changes": [], "audio": {"available": True}}
        candidate = _candidate_from_segment(segment, 120.0, visual)
        
        assert any("speech" in warning.lower() or "no" in warning.lower() for warning in candidate.warnings)


class TestNoSpeechCandidates:
    def test_returns_fallback_for_empty_boundaries(self):
        candidates = _no_speech_candidates(60.0, {"scene_changes": [], "audio": {"available": False}}, 5)
        assert len(candidates) == 1
        assert candidates[0].start == 0
        assert "without speech" in candidates[0].reason.lower() or "visual" in candidates[0].category.lower()

    def test_respects_max_candidates_limit(self):
        scene_changes = [i * 10.0 for i in range(1, 8)]
        candidates = _no_speech_candidates(90.0, {"scene_changes": scene_changes, "audio": {"available": True}}, 3)
        assert len(candidates) <= 3

    def test_marks_analysis_source_as_local(self):
        candidates = _no_speech_candidates(30.0, {"scene_changes": [], "audio": {"available": False}}, 1)
        assert all(candidate.analysis_source == "local" for candidate in candidates)


class TestVideoAnalysis:
    def test_analyze_with_speech_segments(self):
        segments = [
            {"start": 10.0, "end": 18.0, "text": "This is an important moment to pay attention to."},
            {"start": 35.0, "end": 42.0, "text": "Never give up on your dreams."},
        ]
        candidates = analyze_video("/nonexistent/test.mp4", 120.0, segments, max_candidates=5)
        
        assert len(candidates) > 0
        assert all(candidate.score >= 0 for candidate in candidates)
        assert all(candidate.duration >= 15.0 for candidate in candidates)
        assert candidates == sorted(candidates, key=lambda c: c.score, reverse=True)

    def test_analyze_without_speech_segments(self):
        segments = [
            {"start": 10.0, "end": 12.0, "text": ""},
            {"start": 30.0, "end": 32.0, "text": None},
        ]
        candidates = analyze_video("/nonexistent/test.mp4", 90.0, segments, max_candidates=5)
        
        assert len(candidates) > 0
        # At least some candidates are generated even with empty/None text
        assert any(candidate.confidence is not None for candidate in candidates)

    def test_candidates_are_spaced_out(self):
        segments = [
            {"start": float(i * 10), "end": float(i * 10 + 5), "text": f"Moment {i}"}
            for i in range(20)
        ]
        candidates = analyze_video("/nonexistent/test.mp4", 300.0, segments, max_candidates=10)
        
        for i, candidate in enumerate(candidates):
            for other in candidates[i+1:]:
                assert abs(candidate.start - other.start) >= 25 or abs(candidate.start - other.start) == 0

    def test_respects_max_candidates_parameter(self):
        segments = [
            {"start": float(i * 5), "end": float(i * 5 + 3), "text": f"Segment {i}"}
            for i in range(30)
        ]
        candidates = analyze_video("/nonexistent/test.mp4", 300.0, segments, max_candidates=8)
        assert len(candidates) <= 8

    def test_returns_sorted_by_score(self):
        segments = [
            {"start": 10.0, "end": 18.0, "text": "Why is this important? Here are seven reasons to remember this."},
            {"start": 50.0, "end": 52.0, "text": "OK."},
            {"start": 85.0, "end": 95.0, "text": "This is a fundamental concept that everyone must understand before proceeding."},
        ]
        candidates = analyze_video("/nonexistent/test.mp4", 120.0, segments, max_candidates=10)
        
        scores = [c.score for c in candidates]
        assert scores == sorted(scores, reverse=True)
