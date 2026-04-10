"""In-memory interview session state management."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InterviewSession:
    interview_id: str
    domain: str
    role_level: str
    difficulty: str
    duration_minutes: int
    topic_plan: list[dict]
    messages: list[dict] = field(default_factory=list)
    current_topic_index: int = 0
    exchanges_on_current_topic: int = 0
    topics_covered: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    status: str = "setup"

    @property
    def elapsed_seconds(self) -> float:
        if not self.started_at:
            return 0.0
        return (datetime.now() - self.started_at).total_seconds()

    @property
    def remaining_seconds(self) -> float:
        return max(0, self.duration_minutes * 60 - self.elapsed_seconds)

    @property
    def elapsed_minutes(self) -> float:
        return self.elapsed_seconds / 60

    @property
    def remaining_minutes(self) -> float:
        return self.remaining_seconds / 60

    @property
    def elapsed_pct(self) -> float:
        total = self.duration_minutes * 60
        return min(100, (self.elapsed_seconds / total) * 100) if total > 0 else 100

    @property
    def is_time_up(self) -> bool:
        return self.remaining_seconds <= 0

    def add_message(self, role: str, content: str) -> dict:
        msg = {
            "role": role,
            "content": content,
            "elapsed_seconds": self.elapsed_seconds,
        }
        self.messages.append(msg)
        if role == "candidate":
            self.exchanges_on_current_topic += 1
        return msg

    def advance_topic(self) -> None:
        if self.current_topic_index < len(self.topic_plan):
            self.topics_covered.append(
                self.topic_plan[self.current_topic_index]["name"]
            )
        self.current_topic_index += 1
        self.exchanges_on_current_topic = 0

    @property
    def current_topic(self) -> dict | None:
        if self.current_topic_index < len(self.topic_plan):
            return self.topic_plan[self.current_topic_index]
        return None

    @property
    def topics_remaining(self) -> int:
        return max(0, len(self.topic_plan) - self.current_topic_index)


class SessionStore:
    """Simple in-memory session store."""

    def __init__(self):
        self._sessions: dict[str, InterviewSession] = {}

    def create(self, session: InterviewSession) -> None:
        self._sessions[session.interview_id] = session

    def get(self, interview_id: str) -> InterviewSession | None:
        return self._sessions.get(interview_id)

    def remove(self, interview_id: str) -> None:
        self._sessions.pop(interview_id, None)
