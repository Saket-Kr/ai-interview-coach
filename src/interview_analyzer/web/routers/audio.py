"""Audio upload and transcription endpoint."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from interview_analyzer.web.dependencies import get_sessions, get_whisper
from interview_analyzer.web.schemas import AudioTranscriptResponse
from interview_analyzer.web.services.session_manager import SessionStore
from interview_analyzer.web.services.whisper_service import WhisperService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{interview_id}/audio", response_model=AudioTranscriptResponse)
async def upload_audio(
    interview_id: str,
    file: UploadFile = File(...),
    whisper: WhisperService = Depends(get_whisper),
    sessions: SessionStore = Depends(get_sessions),
):
    session = sessions.get(interview_id)
    if not session:
        raise HTTPException(404, "Interview session not found")
    if session.status != "in_progress":
        raise HTTPException(400, "Interview is not in progress")

    audio_bytes = await file.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(400, "Audio too short")

    # Determine format from content type or filename
    audio_format = "webm"
    if file.content_type and "ogg" in file.content_type:
        audio_format = "ogg"
    elif file.filename and "." in file.filename:
        audio_format = file.filename.rsplit(".", 1)[-1]

    # Transcribe in-memory — no file saved to disk
    text = await asyncio.to_thread(whisper.transcribe, audio_bytes, audio_format)

    if not text or len(text.strip()) < 2:
        raise HTTPException(400, "Could not transcribe audio — no speech detected")

    return AudioTranscriptResponse(
        text=text,
        elapsed_seconds=session.elapsed_seconds,
        message_id=0,
    )
