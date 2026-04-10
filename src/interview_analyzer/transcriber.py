import logging
from pathlib import Path

import whisperx

from interview_analyzer.config import Config
from interview_analyzer.models import Segment, Transcript

logger = logging.getLogger(__name__)


def transcribe(audio_path: Path, config: Config) -> Transcript:
    """Transcribe an audio file with optional speaker diarization using WhisperX."""
    logger.info("Loading WhisperX model '%s' on %s", config.whisper_model, config.whisper_device)
    model = whisperx.load_model(
        config.whisper_model,
        device=config.whisper_device,
        compute_type=config.whisper_compute_type,
    )

    logger.info("Transcribing %s", audio_path)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, batch_size=16)

    # Align whisper output for accurate word-level timestamps
    logger.info("Aligning transcript")
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], device=config.whisper_device
    )
    result = whisperx.align(
        result["segments"], align_model, metadata, audio, config.whisper_device,
        return_char_alignments=False,
    )

    # Speaker diarization — requires HuggingFace token for pyannote models
    if config.hf_token:
        try:
            from whisperx.diarize import DiarizationPipeline

            logger.info("Running speaker diarization")
            diarize_model = DiarizationPipeline(
                token=config.hf_token, device=config.whisper_device
            )
            diarize_segments = diarize_model(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)
        except Exception as e:
            logger.warning("Diarization failed (%s), proceeding without speaker labels", e)
    else:
        logger.info(
            "No HuggingFace token provided (--hf-token), skipping diarization. "
            "Speaker identification will be inferred by the LLM from content."
        )

    # Build structured transcript
    segments: list[Segment] = []
    speakers_seen: set[str] = set()

    for seg in result["segments"]:
        speaker = seg.get("speaker", "SPEAKER")
        speakers_seen.add(speaker)
        segments.append(
            Segment(
                speaker=speaker,
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
            )
        )

    # Merge consecutive segments from the same speaker
    merged = _merge_consecutive(segments)
    speakers = sorted(speakers_seen)

    logger.info("Transcription complete: %d segments, %d speakers", len(merged), len(speakers))
    return Transcript(segments=merged, speakers=speakers)


def _merge_consecutive(segments: list[Segment]) -> list[Segment]:
    """Merge consecutive segments from the same speaker into one."""
    if not segments:
        return []

    merged: list[Segment] = [segments[0].model_copy()]
    for seg in segments[1:]:
        if seg.speaker == merged[-1].speaker:
            merged[-1].text += " " + seg.text
            merged[-1].end = seg.end
        else:
            merged.append(seg.model_copy())
    return merged
