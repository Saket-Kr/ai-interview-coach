"""Pydantic request/response schemas for the web API."""

from typing import Literal

from pydantic import BaseModel


DOMAINS = [
    "System Design",
    "Agentic AI",
    "RAG & Information Retrieval",
    "LLM Engineering",
    "Data Structures & Algorithms",
    "Backend Engineering",
]

ROLE_LEVELS = [
    "Junior (0-2y)",
    "Mid (2-5y)",
    "Senior (5-8y)",
    "Staff/Principal (8+y)",
]

DIFFICULTIES = ["easy", "medium", "hard"]
DURATIONS = [30, 45, 60, 90]


class InterviewCreateRequest(BaseModel):
    domain: str
    role_level: str
    difficulty: str
    duration_minutes: int


class InterviewCreateResponse(BaseModel):
    interview_id: str
    redirect_url: str


class AudioTranscriptResponse(BaseModel):
    text: str
    elapsed_seconds: float
    message_id: int


class InterviewSummary(BaseModel):
    id: str
    domain: str
    role_level: str
    difficulty: str
    duration_minutes: int
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    overall_score: float | None = None
    created_at: str


class MessageSchema(BaseModel):
    id: int
    role: str
    content: str
    elapsed_seconds: float
    created_at: str


# WebSocket message types

class WSClientMessage(BaseModel):
    type: Literal["start", "candidate_message", "end"]
    text: str | None = None


class WSServerMessage(BaseModel):
    type: str
    content: str | None = None
    elapsed_seconds: float | None = None
    remaining_seconds: float | None = None
    status: str | None = None
    overall_score: float | None = None
    report_url: str | None = None
    message: str | None = None
