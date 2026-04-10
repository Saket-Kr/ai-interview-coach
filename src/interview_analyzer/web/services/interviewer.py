"""Core interviewer logic: topic planning, conversation, state tracking."""

import json
import logging
import re

from openai import OpenAI

from interview_analyzer.config import Config
from interview_analyzer.web.prompts.interviewer_system import (
    build_interviewer_system_prompt,
    build_topic_planning_prompt,
)
from interview_analyzer.web.services.session_manager import InterviewSession

logger = logging.getLogger(__name__)


def _llm_call(client: OpenAI, config: Config, messages: list[dict], max_tokens: int = 256, temperature: float = 0.7) -> str:
    """Make a chat completion call and return the response content."""
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


def _parse_json(raw: str) -> dict | list:
    """Extract and parse JSON from an LLM response."""
    text = raw.strip()
    # Strip <think>...</think> blocks (Qwen reasoning)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def generate_topic_plan(
    domain: str,
    role_level: str,
    difficulty: str,
    duration_minutes: int,
    config: Config,
) -> list[dict]:
    """Generate a structured topic plan for the interview."""
    client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
    messages = build_topic_planning_prompt(domain, role_level, difficulty, duration_minutes)
    raw = _llm_call(client, config, messages, max_tokens=2048, temperature=0.5)
    data = _parse_json(raw)
    # Handle both {"topics": [...]} and direct [...] responses
    if isinstance(data, list):
        topics = data
    else:
        topics = data.get("topics", [])
    logger.info("Generated topic plan with %d topics", len(topics))
    return topics


def generate_interviewer_response(session: InterviewSession, config: Config) -> str:
    """Generate the next interviewer message based on conversation history."""
    client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

    # Build system prompt with current state
    system_prompt = build_interviewer_system_prompt(session)

    # Build message history for LLM
    messages = [{"role": "system", "content": system_prompt}]
    for msg in session.messages:
        role = "assistant" if msg["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": msg["content"]})

    raw = _llm_call(client, config, messages, max_tokens=256, temperature=0.7)

    # Strip any <think> blocks from the response
    response = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Detect if the LLM is transitioning topics (heuristic)
    _detect_topic_transition(session, response)

    return response


def generate_closing_message(session: InterviewSession, config: Config) -> str:
    """Generate a natural closing message when time is up."""
    if session.elapsed_pct >= 100:
        return (
            "That's our time! Thanks for the great conversation — I really enjoyed "
            "discussing these topics with you. Your interview analysis will be ready "
            "in a moment. Best of luck!"
        )

    # If user ended early, generate a natural closing
    client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
    system_prompt = build_interviewer_system_prompt(session)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in session.messages:
        role = "assistant" if msg["role"] == "interviewer" else "user"
        messages.append({"role": role, "content": msg["content"]})
    messages.append({
        "role": "system",
        "content": "The candidate has ended the interview. Generate a brief, warm closing message thanking them."
    })
    raw = _llm_call(client, config, messages, max_tokens=100, temperature=0.7)
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()


def generate_nudge_message(session: InterviewSession) -> str:
    """Generate a nudge when the candidate hasn't responded."""
    return "Take your time. Would you like me to rephrase the question, or shall we move to a different topic?"


def _detect_topic_transition(session: InterviewSession, response: str) -> None:
    """Detect if the interviewer is transitioning to a new topic."""
    transition_signals = [
        "let's switch", "let's move on", "different topic", "different area",
        "switch gears", "next topic", "moving on", "let's talk about",
        "let's shift", "another area",
    ]
    response_lower = response.lower()
    if any(signal in response_lower for signal in transition_signals):
        session.advance_topic()
    elif session.exchanges_on_current_topic >= 4:
        # After 4 exchanges, assume we're naturally transitioning
        session.advance_topic()
