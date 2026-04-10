"""Singleton Whisper model manager for fast audio transcription."""

import logging
import os
import tempfile

import whisperx

from interview_analyzer.config import Config

logger = logging.getLogger(__name__)


class WhisperService:
    """Load Whisper model once at startup, transcribe many audio chunks."""

    def __init__(self, config: Config):
        logger.info("Loading WhisperX model '%s' on %s", config.whisper_model, config.whisper_device)
        self._model = whisperx.load_model(
            config.whisper_model,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
        )
        self._device = config.whisper_device

    def transcribe(self, audio_bytes: bytes, audio_format: str = "webm") -> str:
        """Transcribe audio bytes to text string.

        Skips alignment and diarization — only need raw text for short
        single-speaker clips in the mock interview.
        """
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            audio = whisperx.load_audio(temp_path)
            result = self._model.transcribe(audio, batch_size=16)
            segments = result.get("segments", [])
            text = " ".join(seg["text"].strip() for seg in segments)
            return text.strip()
        finally:
            os.unlink(temp_path)
