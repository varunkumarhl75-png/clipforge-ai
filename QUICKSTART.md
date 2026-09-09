# ClipForge AI — Quick Start

1. Install **FFmpeg + FFprobe** and make sure both work in PowerShell:
   `ffmpeg -version` and `ffprobe -version`
2. Backend terminal:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
3. Frontend terminal:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
4. Open `http://localhost:3000`.
5. Create a project, choose a local video or paste a YouTube URL, then create it.
6. Wait for **Completed**. Open the project and use **Generate AI Transcript**.
7. Use Shorts, Captions, Repurpose and Long Form from the left menu.

Swagger API: `http://localhost:8000/docs`

### AI model
The first transcription downloads the Whisper model. `WHISPER_MODEL=small` is the default. Use `tiny` or `base` on lower-spec PCs.
