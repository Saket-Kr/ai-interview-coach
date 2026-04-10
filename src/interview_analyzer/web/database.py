"""SQLite database setup and operations."""

import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS interviews (
    id              TEXT PRIMARY KEY,
    domain          TEXT NOT NULL,
    role_level      TEXT NOT NULL,
    difficulty      TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'setup',
    started_at      TEXT,
    ended_at        TEXT,
    overall_score   REAL,
    report_json     TEXT,
    topic_plan_json TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_id    TEXT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    elapsed_seconds REAL NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_interview_id ON messages(interview_id);
CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);
CREATE INDEX IF NOT EXISTS idx_interviews_created_at ON interviews(created_at DESC);
"""

_db_path: str = ""


async def init_db(db_path: str) -> None:
    """Initialize the database with schema."""
    global _db_path
    _db_path = db_path
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    logger.info("Database initialized at %s", db_path)


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    return db


# --- Interview CRUD ---


async def create_interview(
    db: aiosqlite.Connection,
    interview_id: str,
    domain: str,
    role_level: str,
    difficulty: str,
    duration_minutes: int,
    topic_plan_json: str,
) -> None:
    await db.execute(
        """INSERT INTO interviews (id, domain, role_level, difficulty, duration_minutes, topic_plan_json)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (interview_id, domain, role_level, difficulty, duration_minutes, topic_plan_json),
    )
    await db.commit()


async def update_interview(db: aiosqlite.Connection, interview_id: str, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [interview_id]
    await db.execute(
        f"UPDATE interviews SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
        values,
    )
    await db.commit()


async def get_interview(db: aiosqlite.Connection, interview_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM interviews WHERE id = ?", (interview_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def list_interviews(db: aiosqlite.Connection, limit: int = 50, offset: int = 0) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM interviews ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def delete_interview(db: aiosqlite.Connection, interview_id: str) -> None:
    await db.execute("DELETE FROM interviews WHERE id = ?", (interview_id,))
    await db.commit()


# --- Message CRUD ---


async def add_message(
    db: aiosqlite.Connection,
    interview_id: str,
    role: str,
    content: str,
    elapsed_seconds: float,
) -> int:
    cursor = await db.execute(
        """INSERT INTO messages (interview_id, role, content, elapsed_seconds)
        VALUES (?, ?, ?, ?)""",
        (interview_id, role, content, elapsed_seconds),
    )
    await db.commit()
    return cursor.lastrowid


async def get_messages(db: aiosqlite.Connection, interview_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM messages WHERE interview_id = ? ORDER BY id",
        (interview_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
