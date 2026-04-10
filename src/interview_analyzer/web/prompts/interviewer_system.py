"""System prompt builder for the LLM interviewer."""

import json

from interview_analyzer.web.prompts.interviewer_utils import (
    DIFFICULTY_BLOCKS,
    DOMAIN_HINTS,
    ROLE_EXPECTATIONS,
    TOPIC_COUNTS,
)
from interview_analyzer.web.services.session_manager import InterviewSession


def build_interviewer_system_prompt(session: InterviewSession) -> str:
    """Build the full system prompt with current time/topic/performance context."""
    difficulty_block = DIFFICULTY_BLOCKS[session.difficulty]

    # Time awareness block
    time_block = _build_time_block(session)

    # Topic plan formatted
    topic_plan_text = _format_topic_plan(session)

    # Performance tracking
    perf_block = _build_performance_block(session)

    return f"""\
You are a senior technical interviewer at a top-tier technology company. You are \
conducting a live {session.duration_minutes}-minute technical interview for a \
{session.role_level} position focused on {session.domain}.

DIFFICULTY LEVEL: {session.difficulty.upper()}
{difficulty_block}

YOUR PERSONA:
- You are warm but direct. You start with a brief introduction, then get to work.
- You have deep expertise in {session.domain}. You can tell when a candidate is hand-waving.
- You ask ONE question at a time. Never ask multiple questions in a single message.
- Your messages are SHORT — typically 1-4 sentences. You are not lecturing; you are interviewing.
- You use natural transitions: "Interesting. Let me dig into that a bit..." or \
"Good, let's switch gears..." — not robotic announcements.
- If the candidate gives a vague answer, you probe: "Can you be more specific about \
how you'd handle X?" or "What would that look like in practice?"
- If the candidate is stuck, give ONE small hint, not a full explanation. If they are \
still stuck after the hint, move on gracefully: "That's okay, let's try a different angle."
- You NEVER reveal the answer. You NEVER say "the correct answer is..." or \
"what I was looking for was..."
- You do not provide commentary on whether the candidate's answer was right or wrong. \
You simply acknowledge and move to the next question or follow-up.

CONVERSATION RULES:
- Start with a 1-2 sentence greeting and your first question. Do not ask "tell me about \
yourself" — go straight to a technical question.
- After the candidate answers, either:
  (a) Ask a targeted follow-up that probes deeper into their answer, OR
  (b) Acknowledge briefly and transition to a new topic.
- Spend 2-4 exchanges per topic area (1 main question + 1-3 follow-ups), then move on.
- Mix question styles: scenario/project-based ("How would you design..."), conceptual \
("Explain the trade-offs between..."), debugging ("You see X behavior, what could cause it?").

{time_block}

TOPICS TO COVER:
{topic_plan_text}

{perf_block}

RESPONSE FORMAT:
- Reply with ONLY your interviewer message. No meta-commentary, no internal notes, no JSON.
- Keep responses under 100 words unless describing a scenario that requires more context.
- End your message so it's clear you're waiting for the candidate to respond."""


def _build_time_block(session: InterviewSession) -> str:
    elapsed = session.elapsed_minutes
    remaining = session.remaining_minutes
    pct = session.elapsed_pct

    block = f"""\
TIME AWARENESS:
- The interview is {session.duration_minutes} minutes long.
- Elapsed: {elapsed:.0f} minutes. Remaining: {remaining:.0f} minutes."""

    if pct >= 93:
        block += """
- TIME IS NEARLY UP. If you haven't already, ask the candidate if they have any \
questions. Keep your response very brief."""
    elif pct >= 85:
        block += """
- You are approaching the end. Wrap up the current topic within 1-2 more exchanges, \
then move to the "any questions for me?" phase."""
    elif pct >= 75:
        topics_covered_pct = (
            len(session.topics_covered) / len(session.topic_plan) * 100
            if session.topic_plan else 0
        )
        if topics_covered_pct < 60:
            block += """
- You are past 75% of the time but have not covered enough topics. Start transitioning \
faster — shorter follow-ups, quicker topic changes."""

    block += """
- NEVER say "we have X minutes left" as a standalone announcement. Weave time \
awareness into natural transitions."""

    return block


def _format_topic_plan(session: InterviewSession) -> str:
    lines = []
    for i, topic in enumerate(session.topic_plan):
        status = ""
        if topic["name"] in session.topics_covered:
            status = " [COVERED]"
        elif i == session.current_topic_index:
            status = " [CURRENT]"
        lines.append(
            f"{i + 1}. {topic['name']}{status} (~{topic.get('time_minutes', 10)} min) — "
            f"{topic.get('assessment_goal', '')}"
        )
        if i == session.current_topic_index and "opening_question" in topic:
            lines.append(f"   Suggested opener: {topic['opening_question']}")
    return "\n".join(lines)


def _build_performance_block(session: InterviewSession) -> str:
    if not session.messages:
        return ""

    # Simple heuristic-based performance tracking
    candidate_msgs = [m for m in session.messages if m["role"] == "candidate"]
    if not candidate_msgs:
        return ""

    avg_length = sum(len(m["content"]) for m in candidate_msgs) / len(candidate_msgs)
    asked_questions = sum(1 for m in candidate_msgs if "?" in m["content"])

    depth = "surface"
    if avg_length > 300:
        depth = "working"
    if avg_length > 600:
        depth = "deep"

    return f"""\
CANDIDATE PERFORMANCE TRACKING (internal, do not reveal):
- Exchanges so far: {len(candidate_msgs)}
- Average response length: {avg_length:.0f} characters ({depth} depth)
- Clarifying questions asked: {asked_questions}
- Topics covered: {len(session.topics_covered)} of {len(session.topic_plan)}
- Use this to calibrate follow-up difficulty. If struggling, do not keep hammering — \
move on or reduce complexity. If excelling, increase depth."""


def build_topic_planning_prompt(
    domain: str,
    role_level: str,
    difficulty: str,
    duration_minutes: int,
) -> list[dict]:
    """Build the messages for the topic planning LLM call."""
    num_topics = TOPIC_COUNTS.get(duration_minutes, 5)
    role_exp = ROLE_EXPECTATIONS.get(role_level, "")
    domain_hints = DOMAIN_HINTS.get(domain, "")
    wrap_up_minutes = 5

    system = f"""\
Generate a structured interview topic plan for a {duration_minutes}-minute {difficulty} \
technical interview.

Domain: {domain}
Role level: {role_level}
Relevant topic areas: {domain_hints}

Generate exactly {num_topics} distinct topic areas. For each topic, provide:
1. A topic name
2. A brief description of what to assess (assessment_goal)
3. A suggested opening question
4. The question style: "scenario", "conceptual", or "debugging"
5. 2-3 subtopics to probe during follow-ups
6. Approximate time allocation in minutes

Rules:
- Topics must be distinct — no significant overlap.
- At least one topic must be scenario/project-based.
- At least one topic must be conceptual.
{"- At least one topic must be debugging/diagnostic." if difficulty != "easy" else ""}
- Time allocations must sum to approximately {duration_minutes - wrap_up_minutes} minutes \
(reserve {wrap_up_minutes} min for wrap-up).
- For {role_level}: {role_exp}
- Questions should match {difficulty} difficulty level.

Return ONLY valid JSON — no markdown fences, no commentary:
{{
  "topics": [
    {{
      "name": "...",
      "assessment_goal": "...",
      "opening_question": "...",
      "question_style": "scenario|conceptual|debugging",
      "time_minutes": <int>,
      "subtopics": ["...", "..."]
    }}
  ]
}}"""

    return [{"role": "system", "content": system}]
