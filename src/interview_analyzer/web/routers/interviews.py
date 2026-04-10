"""REST endpoints for interview CRUD and analysis."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from interview_analyzer.config import Config
from interview_analyzer.web import database as db
from interview_analyzer.web.dependencies import get_config, get_sessions
from interview_analyzer.web.schemas import InterviewCreateRequest, InterviewCreateResponse, InterviewSummary
from interview_analyzer.web.services.analysis_bridge import analyze_mock_interview
from interview_analyzer.web.services.interviewer import generate_topic_plan
from interview_analyzer.web.services.session_manager import InterviewSession, SessionStore

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=InterviewCreateResponse)
async def create_interview(
    body: InterviewCreateRequest,
    config: Config = Depends(get_config),
    sessions: SessionStore = Depends(get_sessions),
):
    interview_id = uuid.uuid4().hex

    # Generate topic plan via LLM
    topic_plan = await asyncio.to_thread(
        generate_topic_plan,
        body.domain, body.role_level, body.difficulty, body.duration_minutes, config,
    )

    # Persist to DB
    conn = await db.get_db()
    try:
        await db.create_interview(
            conn, interview_id, body.domain, body.role_level,
            body.difficulty, body.duration_minutes, json.dumps(topic_plan),
        )
    finally:
        await conn.close()

    # Create in-memory session
    session = InterviewSession(
        interview_id=interview_id,
        domain=body.domain,
        role_level=body.role_level,
        difficulty=body.difficulty,
        duration_minutes=body.duration_minutes,
        topic_plan=topic_plan,
    )
    sessions.create(session)

    return InterviewCreateResponse(
        interview_id=interview_id,
        redirect_url=f"/interview/{interview_id}",
    )


@router.get("", response_model=list[InterviewSummary])
async def list_interviews(limit: int = 50, offset: int = 0):
    conn = await db.get_db()
    try:
        rows = await db.list_interviews(conn, limit, offset)
    finally:
        await conn.close()
    return rows


@router.get("/{interview_id}")
async def get_interview(interview_id: str):
    conn = await db.get_db()
    try:
        interview = await db.get_interview(conn, interview_id)
        if not interview:
            raise HTTPException(404, "Interview not found")
        messages = await db.get_messages(conn, interview_id)
    finally:
        await conn.close()

    interview["messages"] = messages
    if interview.get("report_json"):
        interview["report"] = json.loads(interview["report_json"])
    return interview


@router.delete("/{interview_id}", status_code=204)
async def delete_interview(
    interview_id: str,
    sessions: SessionStore = Depends(get_sessions),
):
    conn = await db.get_db()
    try:
        await db.delete_interview(conn, interview_id)
    finally:
        await conn.close()
    sessions.remove(interview_id)


@router.post("/{interview_id}/analyze")
async def trigger_analysis(
    interview_id: str,
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_config),
    sessions: SessionStore = Depends(get_sessions),
):
    conn = await db.get_db()
    try:
        interview = await db.get_interview(conn, interview_id)
        if not interview:
            raise HTTPException(404, "Interview not found")
        messages = await db.get_messages(conn, interview_id)
    finally:
        await conn.close()

    # Update status
    conn = await db.get_db()
    try:
        await db.update_interview(conn, interview_id, status="analyzing")
    finally:
        await conn.close()

    msg_dicts = [{"role": m["role"], "content": m["content"], "elapsed_seconds": m["elapsed_seconds"]} for m in messages]
    topic_plan = json.loads(interview.get("topic_plan_json") or "[]")

    background_tasks.add_task(
        _run_analysis,
        interview_id, msg_dicts, topic_plan,
        interview["role_level"], interview["domain"], config,
    )

    return {"status": "analyzing"}


async def _run_analysis(
    interview_id: str,
    messages: list[dict],
    topic_plan: list[dict],
    role_level: str,
    domain: str,
    config: Config,
):
    try:
        result = await asyncio.to_thread(
            analyze_mock_interview, messages, topic_plan, role_level, domain, config,
        )
        conn = await db.get_db()
        try:
            await db.update_interview(
                conn, interview_id,
                status="completed",
                overall_score=result.overall.overall_score,
                report_json=result.model_dump_json(),
            )
        finally:
            await conn.close()
        logger.info("Analysis complete for %s: %.1f/10", interview_id, result.overall.overall_score)
    except Exception:
        logger.exception("Analysis failed for %s", interview_id)
        conn = await db.get_db()
        try:
            await db.update_interview(conn, interview_id, status="error")
        finally:
            await conn.close()
