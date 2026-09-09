# ClipForge AI — Complete Video Repurposing Studio

## Features
- Video upload with streamed large-file handling
- YouTube URL import with yt-dlp
- Background FFmpeg processing + metadata + thumbnail + audio extraction
- Local AI transcription with faster-whisper
- Transcript segment viewer
- SRT and WebVTT caption generation
- Automatic 9:16 Shorts selection and rendering
- Long-form trim/crop/aspect-ratio rendering
- Content repurposing: hooks, titles, captions, hashtags
- Project dashboard and processing progress
- Analytics dashboard
- Channel settings ready for YouTube OAuth/publishing integration
- SQLite persistence and automatic schema migration
- REST API + Swagger docs at `/docs`
- Project detail, Shorts, Long Form, Analytics, Channel, and Settings routes with real backend data
- Persisted processing jobs with startup recovery for interrupted video jobs
- Asynchronous Shorts and Long Form rendering with status polling
- Optional SRT caption burn-in and conservative silence removal for Shorts

## Requirements
- Python 3.11+
- Node.js 20+
- FFmpeg + FFprobe on PATH
- 4–8 GB RAM recommended for the small Whisper model; more is better for larger models

## Windows setup
### Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process Bypass` first.

### Frontend (new terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:3000.

Copy `backend/.env.example` to `backend/.env`. `FFMPEG_PATH` and `FFPROBE_PATH` may be left as `ffmpeg` and `ffprobe` when the executables are on PATH, or set to explicit executable paths. The backend health endpoint reports media-tool readiness without exposing secrets.

## AI transcription
The Transcribe action uses `faster-whisper` locally. The first run downloads the selected model. Set `WHISPER_MODEL` in `backend/.env` to `tiny`, `base`, `small`, `medium`, etc.

## YouTube
Use videos you own or are authorized to process. Public video downloading depends on YouTube access, network conditions and the site's current rules. Cookies can be configured with `YOUTUBE_COOKIES_FILE` when appropriate.

## Important
This is a local development build. Production YouTube OAuth publishing, cloud storage, authentication, payments and multi-user deployment require provider credentials and production infrastructure; the UI/API are structured so those integrations can be added without replacing the core pipeline.

## YouTube publishing
The backend also includes a real YouTube Data API upload endpoint. It deliberately does **not** store OAuth access tokens in SQLite. Supply a valid OAuth 2.0 access token with the `youtube.upload` scope to `POST /api/projects/{id}/youtube/publish`. Use `private` while testing. You must create/configure your own Google Cloud OAuth credentials; ClipForge does not ship credentials.

## Optional integrations and limitations

- Whisper runs locally on CPU by default. A video with no speech returns a completed transcript with zero segments.
- Content-package generation requires `OPENAI_API_KEY`; without it, the API reports that configuration is required instead of fabricating content.
- A YouTube channel ID is metadata only and never implies OAuth authorization. Analytics and publishing require configured Google credentials and an authorized token.
- Video processing jobs are persisted and interrupted processing jobs are requeued on startup. Shorts and edit rendering remain synchronous API operations in this local build.
- Shorts and edit rendering are queued background operations; poll their status endpoints until `completed` or `failed`.

Run backend tests with:

```powershell
cd "C:\Users\varun\OneDrive\Desktop\yt storts\yt video editer\backend"
& "C:\Users\varun\OneDrive\Desktop\yt storts\.venv\Scripts\python.exe" -m pytest -q tests
```
