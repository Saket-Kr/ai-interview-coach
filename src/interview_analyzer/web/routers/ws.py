"""WebSocket endpoint for the live interview conversation."""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from interview_analyzer.config import Config
from interview_analyzer.web import database as db
from interview_analyzer.web.services.interviewer import (
    generate_closing_message,
    generate_interviewer_response,
)
from interview_analyzer.web.services.session_manager import InterviewSession, SessionStore

logger = logging.getLogger(__name__)
router = APIRouter()


async def _send(ws: WebSocket, msg_type: str, **kwargs):
    """Send a typed JSON message over WebSocket."""
    await ws.send_json({"type": msg_type, **kwargs})


@router.websocket("/ws/interview/{interview_id}")
async def interview_websocket(websocket: WebSocket, interview_id: str):
    await websocket.accept()

    app = websocket.app
    config: Config = app.state.config
    sessions: SessionStore = app.state.sessions
    session = sessions.get(interview_id)

    if not session:
        await _send(websocket, "error", message="Interview session not found")
        await websocket.close()
        return

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type = raw.get("type")

            if msg_type == "start":
                await _handle_start(websocket, session, config)

            elif msg_type == "candidate_message":
                text = raw.get("text", "").strip()
                if not text:
                    continue
                await _handle_candidate_message(websocket, session, config, text)

            elif msg_type == "end":
                await _handle_end(websocket, session, config)
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for interview %s", interview_id)
        if session.status == "in_progress":
            session.status = "abandoned"
            conn = await db.get_db()
            try:
                await db.update_interview(conn, interview_id, status="abandoned")
            finally:
                await conn.close()
    except Exception:
        logger.exception("WebSocket error for interview %s", interview_id)
        await _send(websocket, "error", message="An unexpected error occurred")


async def _handle_start(ws: WebSocket, session: InterviewSession, config: Config):
    """Start the interview — generate first question."""
    session.started_at = datetime.now()
    session.status = "in_progress"

    conn = await db.get_db()
    try:
        await db.update_interview(
            conn, session.interview_id,
            status="in_progress",
            started_at=session.started_at.isoformat(),
        )
    finally:
        await conn.close()

    # Generate opening message
    await _send(ws, "thinking")
    response = await asyncio.to_thread(generate_interviewer_response, session, config)
    session.add_message("interviewer", response)

    conn = await db.get_db()
    try:
        await db.add_message(conn, session.interview_id, "interviewer", response, 0.0)
    finally:
        await conn.close()

    await _send(ws, "interviewer_message", content=response, elapsed_seconds=0.0)
    await _send(ws, "timer_sync",
                elapsed_seconds=session.elapsed_seconds,
                remaining_seconds=session.remaining_seconds)


async def _handle_candidate_message(
    ws: WebSocket, session: InterviewSession, config: Config, text: str,
):
    """Process candidate message and generate interviewer follow-up."""
    # Add candidate message
    session.add_message("candidate", text)
    conn = await db.get_db()
    try:
        await db.add_message(conn, session.interview_id, "candidate", text, session.elapsed_seconds)
    finally:
        await conn.close()

    # Check if time is up
    if session.is_time_up:
        await _handle_end(ws, session, config)
        return

    # Generate interviewer response
    await _send(ws, "thinking")
    response = await asyncio.to_thread(generate_interviewer_response, session, config)
    session.add_message("interviewer", response)

    conn = await db.get_db()
    try:
        await db.add_message(conn, session.interview_id, "interviewer", response, session.elapsed_seconds)
    finally:
        await conn.close()

    await _send(ws, "interviewer_message", content=response, elapsed_seconds=session.elapsed_seconds)
    await _send(ws, "timer_sync",
                elapsed_seconds=session.elapsed_seconds,
                remaining_seconds=session.remaining_seconds)

    # Check if time is up after response
    if session.is_time_up:
        await _handle_end(ws, session, config)


async def _handle_end(ws: WebSocket, session: InterviewSession, config: Config):
    """End the interview — send closing message and trigger analysis."""
    closing = await asyncio.to_thread(generate_closing_message, session, config)
    session.add_message("interviewer", closing)
    session.status = "completed"

    conn = await db.get_db()
    try:
        await db.add_message(conn, session.interview_id, "interviewer", closing, session.elapsed_seconds)
        await db.update_interview(
            conn, session.interview_id,
            status="completed",
            ended_at=datetime.now().isoformat(),
        )
    finally:
        await conn.close()

    await _send(ws, "interviewer_message", content=closing, elapsed_seconds=session.elapsed_seconds)
    await _send(ws, "status_change", status="completed")

    # Trigger analysis in background — decoupled from WebSocket lifetime
    asyncio.create_task(_run_background_analysis(session, config))


async def _run_background_analysis(session: InterviewSession, config: Config):
    """Run analysis — fully decoupled from WebSocket. Frontend polls for completion."""
    from interview_analyzer.web.services.analysis_bridge import analyze_mock_interview

    interview_id = session.interview_id
    conn = await db.get_db()
    try:
        await db.update_interview(conn, interview_id, status="analyzing")
    finally:
        await conn.close()

    try:
        result = await asyncio.to_thread(
            analyze_mock_interview,
            session.messages, session.topic_plan,
            session.role_level, session.domain, config,
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
        logger.exception("Background analysis failed for %s", interview_id)
        conn = await db.get_db()
        try:
            await db.update_interview(conn, interview_id, status="error")
        finally:
            await conn.close()
        try:
            await _send(ws, "error", message="Analysis failed. You can retry from the dashboard.")
        except Exception:
            pass
