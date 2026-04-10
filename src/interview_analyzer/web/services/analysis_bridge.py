"""Adapter: convert mock interview messages into the existing analysis pipeline."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from interview_analyzer.analyzer import _analyze_single_question, _generate_overall, _llm_call, _parse_json
from interview_analyzer.config import Config
from interview_analyzer.models import (
    AnalysisResult,
    QAPair,
    QuestionAnalysis,
    Segment,
    Transcript,
)

logger = logging.getLogger(__name__)


def build_transcript_from_messages(messages: list[dict]) -> Transcript:
    """Convert chat messages into a Transcript for the analysis pipeline."""
    segments = []
    for msg in messages:
        speaker = "INTERVIEWER" if msg["role"] == "interviewer" else "CANDIDATE"
        segments.append(Segment(
            speaker=speaker,
            text=msg["content"],
            start=msg["elapsed_seconds"],
            end=msg["elapsed_seconds"] + 1.0,
        ))
    return Transcript(segments=segments, speakers=["INTERVIEWER", "CANDIDATE"])


def build_qa_pairs_from_messages(messages: list[dict]) -> list[QAPair]:
    """Build QAPairs directly from conversation — no LLM extraction needed."""
    qa_pairs = []
    question_num = 0
    i = 0

    while i < len(messages):
        if messages[i]["role"] == "interviewer":
            question_text = messages[i]["content"]
            answer_parts = []
            j = i + 1
            while j < len(messages) and messages[j]["role"] == "candidate":
                answer_parts.append(messages[j]["content"])
                j += 1
            if answer_parts:
                question_num += 1
                qa_pairs.append(QAPair(
                    question_number=question_num,
                    question=question_text,
                    answer=" ".join(answer_parts),
                    topic="General",
                ))
            i = j
        else:
            i += 1

    return qa_pairs


def tag_qa_topics(qa_pairs: list[QAPair], topic_plan: list[dict], config: Config) -> list[QAPair]:
    """Use LLM to tag each QA pair with the most relevant topic from the plan."""
    if not qa_pairs or not topic_plan:
        return qa_pairs

    topic_names = [t["name"] for t in topic_plan]
    client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

    system = f"""\
You are labeling interview Q&A pairs with their topic. Available topics: {json.dumps(topic_names)}.

For each Q&A pair, assign the single most relevant topic from the list above.

Return ONLY valid JSON — no markdown fences:
{{"topics": ["topic_for_q1", "topic_for_q2", ...]}}"""

    qa_summary = "\n".join(
        f"Q{qa.question_number}: {qa.question[:200]}" for qa in qa_pairs
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": qa_summary},
    ]

    try:
        raw = _llm_call(client, config, messages)
        data = _parse_json(raw)
        topics = data.get("topics", [])
        for i, qa in enumerate(qa_pairs):
            if i < len(topics) and topics[i] in topic_names:
                qa.topic = topics[i]
    except Exception:
        logger.warning("Topic tagging failed, using default topics")

    return qa_pairs


def analyze_mock_interview(
    messages: list[dict],
    topic_plan: list[dict],
    role_level: str,
    domain: str,
    config: Config,
) -> AnalysisResult:
    """Run the full analysis pipeline on a completed mock interview."""
    client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

    # Build compatible objects
    transcript = build_transcript_from_messages(messages)
    qa_pairs = build_qa_pairs_from_messages(messages)
    qa_pairs = tag_qa_topics(qa_pairs, topic_plan, config)

    logger.info("Analyzing %d Q&A pairs", len(qa_pairs))

    # Per-question analysis — reuse existing pipeline
    question_analyses: list[QuestionAnalysis] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(
                _analyze_single_question,
                client, config, qa, role_level, transcript, None, None,
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

    question_analyses.sort(key=lambda a: a.qa.question_number)

    # Overall assessment
    logger.info("Generating overall assessment")
    overall = _generate_overall(client, config, question_analyses, role_level, None, None)

    return AnalysisResult(
        transcript=transcript,
        qa_pairs=qa_pairs,
        question_analyses=question_analyses,
        overall=overall,
    )
