from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import router
from app.db.database import init_db
from app.services.file_service import ensure_storage_dirs
from app.services.job_processor import processor


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    ensure_storage_dirs()
    processor.recover()
    yield


app = FastAPI(
    title="NyxarClip AI",
    version="2.0.0",
    description="AI video repurposing studio",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "https://nyxar-clips-frontend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "NyxarClip AI",
        "docs": "/docs",
        "status": "running",
    }