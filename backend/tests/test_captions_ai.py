from pathlib import Path
import base64
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core import settings
from app.db.database import SessionLocal
from app.main import app
from app.models import Project, Transcript, TranscriptSegment
from app.services.caption_service import format_srt_timestamp, format_vtt_timestamp, write_captions
from app.services.ai import get_ai_provider
from app.services.ai.providers.gemini import GeminiProvider
from app.services.ai.base import GeneratedImage
from app.api import routes


def create_project(name: str) -> str:
    with TestClient(app) as client:
        response = client.post("/api/projects", json={"name": name})
        assert response.status_code == 200
        return response.json()["id"]


def add_transcript(project_id: str, segments: list[dict]) -> None:
    db = SessionLocal()
    try:
        db.add(Transcript(project_id=project_id, language="en", full_text=" ".join(s["text"] for s in segments), status="completed"))
        db.add_all([TranscriptSegment(project_id=project_id, **segment) for segment in segments])
        db.commit()
    finally:
        db.close()


def test_caption_formatters_skip_empty_segments_and_preserve_unicode(tmp_path: Path):
    srt_path, vtt_path = write_captions(
        "format-test",
        [{"start": 1.5, "end": 2.5, "text": ""}, {"start": 3, "end": 4, "text": "Café"}],
        tmp_path,
    )

    assert format_srt_timestamp(7.5) == "00:00:07,500"
    assert format_vtt_timestamp(7.5) == "00:00:07.500"
    assert Path(srt_path).read_text(encoding="utf-8") == "1\n00:00:03,000 --> 00:00:04,000\nCafé\n"
    assert Path(vtt_path).read_text(encoding="utf-8") == "WEBVTT\n\n00:00:03.000 --> 00:00:04.000\nCafé\n"


def test_caption_generation_and_downloads_use_database_segments():
    project_id = create_project("Caption API test")
    add_transcript(project_id, [{"start": 0.0, "end": 1.25, "text": "Hello"}])

    with TestClient(app) as client:
        generated = client.post(f"/api/projects/{project_id}/captions")
        assert generated.status_code == 200
        assert generated.json()["segment_count"] == 1
        assert generated.json()["srt"] == f"/api/projects/{project_id}/captions/srt"
        assert "C:\\" not in generated.text

        metadata = client.get(f"/api/projects/{project_id}/captions")
        assert metadata.status_code == 200
        assert metadata.json()["language"] == "en"

        srt = client.get(f"/api/projects/{project_id}/captions/srt")
        vtt = client.get(f"/api/projects/{project_id}/captions/vtt")
        assert srt.status_code == 200 and "Hello" in srt.text
        assert vtt.status_code == 200 and vtt.text.startswith("WEBVTT")


def test_caption_generation_reports_zero_speech_segments():
    project_id = create_project("Silent caption test")
    add_transcript(project_id, [])

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/captions")

    assert response.status_code == 400
    assert response.json()["detail"] == "Generate a transcript first. No speech segments are available."


def test_thumbnail_validation_and_missing_gemini_configuration(monkeypatch):
    project_id = create_project("Thumbnail API test")
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")

    with TestClient(app) as client:
        invalid = client.post(f"/api/projects/{project_id}/thumbnail/generate", json={"prompt": " "})
        unavailable = client.post(f"/api/projects/{project_id}/thumbnail/generate", json={"prompt": "A bold gaming thumbnail"})

    assert invalid.status_code == 422
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"] == "Gemini AI is not configured."


def test_thumbnail_rejects_missing_image_model(monkeypatch):
    project_id = create_project("Missing image model test")
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr(settings, "GEMINI_IMAGE_MODEL", "")

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/thumbnail", json={"prompt": "A Python tutorial"})

    assert response.status_code == 503
    assert response.json()["detail"] == "No Gemini image-generation model is configured. Configure GEMINI_IMAGE_MODEL first."


def test_thumbnail_rejects_invalid_project():
    with TestClient(app) as client:
        response = client.post("/api/projects/not-a-project/thumbnail", json={"prompt": "A thumbnail"})

    assert response.status_code == 404


def test_thumbnail_saves_mocked_image_and_returns_safe_media_url(monkeypatch):
    project_id = create_project("Generated thumbnail test")

    class FakeProvider:
        name = "gemini"

        def generate_image(self, prompt: str):
            assert "16:9 YouTube thumbnail" in prompt
            return GeneratedImage(data=b"fake-png-bytes", media_type="image/png")

    monkeypatch.setattr(routes, "get_ai_provider", lambda: FakeProvider())
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "never-return-this")

    with TestClient(app) as client:
        response = client.post(f"/api/projects/{project_id}/thumbnail", json={"prompt": "Python programming tutorial"})
        assert response.status_code == 200
        body = response.json()
        assert body["project_id"] == project_id
        assert body["media_type"] == "image/png"
        assert body["media_url"].startswith(f"/api/projects/{project_id}/thumbnail/generated/")
        assert "storage" not in response.text.lower()
        assert "never-return-this" not in response.text

        media = client.get(body["media_url"])
        assert media.status_code == 200
        assert media.content == b"fake-png-bytes"


def test_ai_provider_abstraction_selects_gemini_without_exposing_credentials(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-only-key")

    provider = get_ai_provider()

    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"


def test_gemini_provider_uses_image_interactions_response_format(monkeypatch):
    provider = GeminiProvider()
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr(settings, "GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    calls = {}

    class FakeInteractions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(output_image=SimpleNamespace(data=base64.b64encode(b"image-bytes").decode(), mime_type="image/png"))

    monkeypatch.setattr(provider, "_client", lambda: SimpleNamespace(interactions=FakeInteractions()))
    image = provider.generate_image("A Python tutorial thumbnail")

    assert image.data == b"image-bytes"
    assert calls["model"] == "gemini-2.5-flash-image"
    assert calls["response_format"] == {"type": "image", "aspect_ratio": "16:9", "image_size": "1K"}
    assert calls["store"] is False