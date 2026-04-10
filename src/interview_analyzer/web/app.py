"""FastAPI application factory and entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from interview_analyzer.config import Config
from interview_analyzer.web.database import init_db
from interview_analyzer.web.routers import audio, interviews, pages, ws
from interview_analyzer.web.services.session_manager import SessionStore
from interview_analyzer.web.services.whisper_service import WhisperService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = Config()
    app.state.config = config
    app.state.sessions = SessionStore()

    # Init database
    await init_db("interviews.db")

    # Load Whisper model once
    logger.info("Loading Whisper model (this may take a moment)...")
    app.state.whisper = WhisperService(config)
    logger.info("Whisper model loaded.")

    yield

    logger.info("Shutting down.")


app = FastAPI(title="Interview Simulator", lifespan=lifespan)

# Static files
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

# Routers
app.include_router(interviews.router, prefix="/api/interviews", tags=["interviews"])
app.include_router(audio.router, prefix="/api/interviews", tags=["audio"])
app.include_router(ws.router, tags=["websocket"])
app.include_router(pages.router, tags=["pages"])


def main():
    """Entry point for the interview-simulator command."""
    uvicorn.run(
        "interview_analyzer.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
