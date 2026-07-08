"""Envio de notificações via Pushover (https://pushover.net)."""

import logging
import os

import httpx

logger = logging.getLogger("reminder-mcp.pushover")

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

PUSHOVER_USER_KEY = os.environ.get("PUSHOVER_USER_KEY", "uxb8y8mdp2a5iaax7w8p7yndiudrzb")
PUSHOVER_APP_TOKEN = os.environ.get("PUSHOVER_APP_TOKEN", "apaoi2jid6pkucmbmvuk4sntmhzpjf")


async def send_notification(title: str, message: str, priority: int = 1) -> bool:
    """Envia uma notificação push via Pushover. Retorna True se enviada com sucesso."""
    try:
        payload = {
            "token": PUSHOVER_APP_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": title[:250],
            "message": message,
            "priority": priority,
        }
        # Prioridade 2 (emergência) exige retry/expire, senão o Pushover
        # rejeita com HTTP 400. Reenvia a cada 60s por até 1h ou até o
        # usuário confirmar o recebimento.
        if priority == 2:
            payload["retry"] = 60
            payload["expire"] = 3600
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(PUSHOVER_API_URL, data=payload)
            if resp.status_code != 200:
                logger.error("Pushover retornou HTTP %s: %s", resp.status_code, resp.text)
                return False
            return True
    except Exception:
        logger.exception("Falha ao enviar notificação Pushover")
        return False
