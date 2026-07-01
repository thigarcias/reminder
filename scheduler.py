"""Loop em background que dispara notificações Pushover para lembretes vencidos."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import reminders
from pushover import send_notification

logger = logging.getLogger("reminder-mcp.scheduler")

CHECK_INTERVAL_SECONDS = 20

_scheduler: AsyncIOScheduler | None = None


async def _check_due_reminders() -> None:
    now = datetime.now(timezone.utc)
    for reminder in reminders.due_reminders(now):
        ok = await send_notification(
            title="Lembrete",
            message=reminder["message"],
        )
        if ok:
            reminders.mark_sent(reminder["id"])
            logger.info("Notificação enviada para lembrete %s", reminder["id"])
        else:
            logger.warning("Falha ao notificar lembrete %s, tentará novamente", reminder["id"])


def start() -> AsyncIOScheduler:
    global _scheduler
    reminders.init_db()
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(_check_due_reminders, "interval", seconds=CHECK_INTERVAL_SECONDS, id="check_due_reminders")
    _scheduler.start()
    logger.info("Scheduler iniciado (verificação a cada %ss)", CHECK_INTERVAL_SECONDS)
    return _scheduler


def stop() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler parado")
