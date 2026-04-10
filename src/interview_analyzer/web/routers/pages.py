"""HTML page routes — serves Jinja2 templates."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from interview_analyzer.web import database as db
from interview_analyzer.web.schemas import DOMAINS, ROLE_LEVELS, DIFFICULTIES, DURATIONS

logger = logging.getLogger(__name__)
router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def setup_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "domains": DOMAINS,
        "role_levels": ROLE_LEVELS,
        "difficulties": DIFFICULTIES,
        "durations": DURATIONS,
    })


@router.get("/interview/{interview_id}", response_class=HTMLResponse)
async def interview_page(request: Request, interview_id: str):
    conn = await db.get_db()
    try:
        interview = await db.get_interview(conn, interview_id)
    finally:
        await conn.close()

    if not interview:
        raise HTTPException(404, "Interview not found")

    return templates.TemplateResponse(request, "interview.html", {
        "interview": interview,
        "interview_id": interview_id,
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    conn = await db.get_db()
    try:
        interviews = await db.list_interviews(conn)
    finally:
        await conn.close()

    return templates.TemplateResponse(request, "dashboard.html", {
        "interviews": interviews,
    })


@router.get("/dashboard/{interview_id}", response_class=HTMLResponse)
async def report_page(request: Request, interview_id: str):
    conn = await db.get_db()
    try:
        interview = await db.get_interview(conn, interview_id)
        if not interview:
            raise HTTPException(404, "Interview not found")
        messages = await db.get_messages(conn, interview_id)
    finally:
        await conn.close()

    report = None
    if interview.get("report_json"):
        report = json.loads(interview["report_json"])

    return templates.TemplateResponse(request, "report.html", {
        "interview": interview,
        "messages": messages,
        "report": report,
    })
