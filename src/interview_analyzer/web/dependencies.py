"""FastAPI dependency injection helpers."""

from fastapi import Request

from interview_analyzer.config import Config
from interview_analyzer.web.services.session_manager import SessionStore
from interview_analyzer.web.services.whisper_service import WhisperService


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_whisper(request: Request) -> WhisperService:
    return request.app.state.whisper


def get_sessions(request: Request) -> SessionStore:
    return request.app.state.sessions
