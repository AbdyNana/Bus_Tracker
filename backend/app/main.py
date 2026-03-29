"""
SUB_Tracker Backend — FastAPI Entry Point
Executive AI Concierge for Bishkek entrepreneurs.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import voice, intent, tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="SUB_Tracker Backend",
    description="Executive AI Concierge — Smart Calendar, Live Booking, Smart Messaging",
    version="1.0.0",
)

# Allow requests from frontend and mobile dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(voice.router, prefix="/api", tags=["STT"])
app.include_router(intent.router, prefix="/api", tags=["Intent"])
app.include_router(tasks.router, prefix="/api", tags=["Calendar"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "SUB_Tracker Backend",
        "status": "online",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/process-voice",
            "POST /api/process-intent",
            "GET  /api/tasks?date=YYYY-MM-DD",
        ],
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
