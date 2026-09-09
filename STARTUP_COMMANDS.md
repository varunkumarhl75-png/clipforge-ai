# Startup Commands

### Terminal 1 — Backend
```powershell
cd "C:\Users\varun\OneDrive\Desktop\yt video editer\backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — Frontend
```powershell
cd "C:\Users\varun\OneDrive\Desktop\yt video editer\frontend"
npm run dev
```

Open: http://localhost:3000
API docs: http://localhost:8000/docs

If you get `Failed to fetch`, confirm Terminal 1 is running on port 8000.
