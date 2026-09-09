from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_media_readiness():
    with TestClient(app) as client:
        response = client.get('/api/health')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    assert response.json()['ffmpeg_available'] is True


def test_project_lifecycle_and_invalid_id():
    with TestClient(app) as client:
        created = client.post('/api/projects', json={'name': 'API test project'})
        assert created.status_code == 200
        project_id = created.json()['id']

        listed = client.get('/api/projects')
        assert listed.status_code == 200
        assert any(project['id'] == project_id for project in listed.json())

        retrieved = client.get(f'/api/projects/{project_id}')
        assert retrieved.status_code == 200
        assert retrieved.json()['name'] == 'API test project'

        missing = client.get('/api/projects/not-a-real-project')
        assert missing.status_code == 404

        deleted = client.delete(f'/api/projects/{project_id}')
        assert deleted.status_code == 200


def test_settings_are_secret_safe_and_urls_are_validated():
    with TestClient(app) as client:
        settings = client.get('/api/settings')
        assert settings.status_code == 200
        assert 'OPENAI_API_KEY' not in settings.text
        assert settings.json()['ffmpeg_available'] is True
        invalid = client.post('/api/projects', json={'name': 'bad url', 'source_type': 'youtube_url', 'source_url': 'https://example.com/video'})
        assert invalid.status_code == 422


def test_short_candidates_cover_timeline_and_default_to_ten():
    from app.services.short_service import suggest_windows

    segments = [
        {'start': minute * 60, 'end': minute * 60 + 8, 'text': 'This is a strong moment with a clear lesson and useful context.'}
        for minute in range(0, 135, 10)
    ]
    candidates = suggest_windows(2 * 60 * 60, segments)
    assert len(candidates) == 10
    assert candidates[0].score >= 0.45
    assert len({int(candidate.start // 600) for candidate in candidates}) >= 8