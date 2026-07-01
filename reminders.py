"""Persistência dos lembretes em SQLite."""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.environ.get("REMINDER_DB_PATH", "reminders.db")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def create_reminder(message: str, remind_at: datetime) -> dict:
    reminder_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO reminders (id, message, remind_at, created_at, sent) VALUES (?, ?, ?, ?, 0)",
            (reminder_id, message, remind_at.isoformat(), created_at),
        )
    return {
        "id": reminder_id,
        "message": message,
        "remind_at": remind_at.isoformat(),
        "created_at": created_at,
        "sent": False,
    }


def list_reminders(include_sent: bool = False) -> list[dict]:
    query = "SELECT * FROM reminders"
    if not include_sent:
        query += " WHERE sent = 0"
    query += " ORDER BY remind_at ASC"
    with _conn() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(r) | {"sent": bool(r["sent"])} for r in rows]


def get_reminder(reminder_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
    if row is None:
        return None
    return dict(row) | {"sent": bool(row["sent"])}


def delete_reminder(reminder_id: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    return cur.rowcount > 0


def due_reminders(now: datetime) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE sent = 0 AND remind_at <= ?",
            (now.isoformat(),),
        ).fetchall()
    return [dict(r) | {"sent": bool(r["sent"])} for r in rows]


def mark_sent(reminder_id: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
