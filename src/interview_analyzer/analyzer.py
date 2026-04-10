"""Orchestrates the full interview analysis pipeline."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

from interview_analyzer.config import Config
from interview_analyzer.models import (
    AnalysisResult,
    CommunicationScore,
    ContentScore,
    InteractionScore,
    OverallAssessment,
    QAPair,
    QuestionAnalysis,
    Transcript,
)
from interview_analyzer.prompts import (
    communication_analysis,
    content_analysis,
    interaction_analysis,
    overall_assessment,
    question_extraction,
)
from interview_analyzer.resume_parser import extract_resume_text
from interview_analyzer.transcriber import transcribe

logger = logging.getLogger(__name__)


def _llm_call(client: OpenAI, config: Config, messages: list[dict]) -> str:
    """Make a chat completion call and return the response content."""
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=messages,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
    )
    return response.choices[0].message.content


def _parse_json(raw: str) -> dict:
    """Extract and parse JSON from an LLM response, handling markdown fences and thinking tags."""
    text = raw.strip()
    # Strip <think>...</think> blocks (Qwen reasoning)
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    # Try to find JSON object in the text if direct parse fails
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Look for first { ... last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def _format_transcript(transcript: Transcript) -> str:
    """Format transcript segments into labeled text for LLM consumption."""
    lines = []
    for seg in transcript.segments:
        lines.append(f"[{seg.speaker}] ({seg.start:.1f}s - {seg.end:.1f}s): {seg.text}")
    return "\n".join(lines)


def _extract_qa_pairs(
    client: OpenAI, config: Config, transcript: Transcript
) -> list[QAPair]:
    """Use LLM to identify Q&A pairs from the transcript."""
    logger.info("Extracting Q&A pairs from transcript")
    transcript_text = _format_transcript(transcript)
    messages = question_extraction.build_messages(transcript_text)
    raw = _llm_call(client, config, messages)
    logger.debug("QA extraction raw response:\n%s", raw[:2000])
    data = _parse_json(raw)

    return [QAPair(**qa) for qa in data["qa_pairs"]]


def _analyze_single_question(
    client: OpenAI,
    config: Config,
    qa: QAPair,
    role: str,
    transcript: Transcript,
    jd_text: str | None,
    resume_text: str | None,
) -> QuestionAnalysis:
    """Run all three analysis dimensions on a single Q&A pair."""
    full_exchange = _format_transcript(transcript)

    # Run content, communication, and interaction analysis in parallel
    results: dict[str, dict] = {}

    def run_content():
        msgs = content_analysis.build_messages(
            qa.question, qa.answer, qa.topic, role, jd_text, resume_text
        )
        return _parse_json(_llm_call(client, config, msgs))

    def run_communication():
        msgs = communication_analysis.build_messages(qa.question, qa.answer)
        return _parse_json(_llm_call(client, config, msgs))

    def run_interaction():
        msgs = interaction_analysis.build_messages(
            qa.question, qa.answer, full_exchange
        )
        return _parse_json(_llm_call(client, config, msgs))

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_content): "content",
            pool.submit(run_communication): "communication",
            pool.submit(run_interaction): "interaction",
        }
        for future in as_completed(futures):
            key = futures[future]
            results[key] = future.result()

    content = ContentScore(**results["content"])
    comms = CommunicationScore(**results["communication"])
    interaction = InteractionScore(**results["interaction"])

    # Compute weighted overall score for this question
    content_avg = (
        content.technical_accuracy
        + content.depth
        + content.specificity
        + content.completeness
        + content.tradeoff_awareness
    ) / 5
    comms_avg = (comms.structure + comms.conciseness + comms.clarity + comms.recovery) / 4
    interaction_avg = (
        interaction.clarifying_questions + interaction.listening + interaction.adaptability
    ) / 3

    # Weight: content 50%, communication 30%, interaction 20%
    overall_score = round(content_avg * 0.5 + comms_avg * 0.3 + interaction_avg * 0.2, 1)

    summary = (
        f"Q{qa.question_number} ({qa.topic}): {overall_score}/10 — "
        f"Content {content_avg:.1f}, Communication {comms_avg:.1f}, "
        f"Interaction {interaction_avg:.1f}"
    )

    return QuestionAnalysis(
        qa=qa,
        content=content,
        communication=comms,
        interaction=interaction,
        overall_score=overall_score,
        summary=summary,
    )


def _generate_overall(
    client: OpenAI,
    config: Config,
    analyses: list[QuestionAnalysis],
    role: str,
    jd_text: str | None,
    resume_text: str | None,
) -> OverallAssessment:
    """Generate the overall assessment from per-question results."""
    logger.info("Generating overall assessment")
    analyses_json = json.dumps(
        [a.model_dump(mode="json") for a in analyses], indent=2
    )
    messages = overall_assessment.build_messages(role, analyses_json, jd_text, resume_text)
    raw = _llm_call(client, config, messages)
    data = _parse_json(raw)
    return OverallAssessment(**data)


def analyze(
    audio_path: Path,
    role: str,
    config: Config,
    jd_path: Path | None = None,
    resume_path: Path | None = None,
) -> AnalysisResult:
    """Run the full interview analysis pipeline."""
    client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

    # Step 1: Transcribe
    logger.info("Step 1/4: Transcribing audio")
    transcript = transcribe(audio_path, config)

    # Step 2: Parse optional inputs
    jd_text = jd_path.read_text() if jd_path else None
    resume_text = extract_resume_text(resume_path) if resume_path else None

    # Step 3: Extract Q&A pairs
    logger.info("Step 2/4: Extracting Q&A pairs")
    qa_pairs = _extract_qa_pairs(client, config, transcript)
    logger.info("Found %d Q&A pairs", len(qa_pairs))

    # Step 4: Analyze each question (parallelized across questions)
    logger.info("Step 3/4: Analyzing %d questions", len(qa_pairs))
    question_analyses: list[QuestionAnalysis] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(
                _analyze_single_question,
                client, config, qa, role, transcript, jd_text, resume_text,
            ): qa.question_number
            for qa in qa_pairs
        }
        for future in as_completed(futures):
            qnum = futures[future]
            try:
                result = future.result()
                question_analyses.append(result)
                logger.info("  Completed analysis for Q%d", qnum)
            except Exception:
                logger.exception("  Failed analysis for Q%d", qnum)
                raise

    # Sort by question number
    question_analyses.sort(key=lambda a: a.qa.question_number)

    # Step 5: Overall assessment
    logger.info("Step 4/4: Generating overall assessment")
    overall = _generate_overall(
        client, config, question_analyses, role, jd_text, resume_text
    )

    return AnalysisResult(
        transcript=transcript,
        qa_pairs=qa_pairs,
        question_analyses=question_analyses,
        overall=overall,
    )
