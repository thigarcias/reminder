"""Persistência dos lembretes em SQLite."""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

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
                sent INTEGER NOT NULL DEFAULT 0,
                recorrencia INTEGER NOT NULL DEFAULT 1,
                recorrencia_intervalo INTEGER,
                ocorrencias_enviadas INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Migração aditiva para bancos criados antes da recorrência existir.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(reminders)")}
        migrations = {
            "recorrencia": "ALTER TABLE reminders ADD COLUMN recorrencia INTEGER NOT NULL DEFAULT 1",
            "recorrencia_intervalo": "ALTER TABLE reminders ADD COLUMN recorrencia_intervalo INTEGER",
            "ocorrencias_enviadas": "ALTER TABLE reminders ADD COLUMN ocorrencias_enviadas INTEGER NOT NULL DEFAULT 0",
        }
        for col, ddl in migrations.items():
            if col not in existing_cols:
                conn.execute(ddl)


def create_reminder(
    message: str,
    remind_at: datetime,
    recorrencia: int = 1,
    recorrencia_intervalo: int | None = None,
) -> dict:
    reminder_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO reminders
                (id, message, remind_at, created_at, sent, recorrencia, recorrencia_intervalo, ocorrencias_enviadas)
            VALUES (?, ?, ?, ?, 0, ?, ?, 0)
            """,
            (reminder_id, message, remind_at.isoformat(), created_at, recorrencia, recorrencia_intervalo),
        )
    return get_reminder(reminder_id)


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


def register_occurrence_sent(reminder_id: str) -> dict | None:
    """Registra que uma ocorrência do lembrete foi notificada.

    Se ainda restarem repetições (ocorrencias_enviadas < recorrencia),
    reagenda remind_at somando recorrencia_intervalo (em segundos) ao
    horário que acabou de disparar. Caso contrário, marca sent = 1.
    """
    reminder = get_reminder(reminder_id)
    if reminder is None:
        return None

    ocorrencias_enviadas = reminder["ocorrencias_enviadas"] + 1
    with _conn() as conn:
        if ocorrencias_enviadas >= reminder["recorrencia"]:
            conn.execute(
                "UPDATE reminders SET sent = 1, ocorrencias_enviadas = ? WHERE id = ?",
                (ocorrencias_enviadas, reminder_id),
            )
        else:
            next_remind_at = datetime.fromisoformat(reminder["remind_at"]) + timedelta(
                seconds=reminder["recorrencia_intervalo"]
            )
            conn.execute(
                "UPDATE reminders SET remind_at = ?, ocorrencias_enviadas = ? WHERE id = ?",
                (next_remind_at.isoformat(), ocorrencias_enviadas, reminder_id),
            )
    return get_reminder(reminder_id)
