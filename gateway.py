"""Servidor MCP de Lembretes.

Expõe tools (create_reminder, list_reminders, delete_reminder) para uma LLM
orquestrar lembretes, e roda em background um agendador que dispara
notificações Pushover no horário programado.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

import reminders
import scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("reminder-mcp")

GATEWAY_AUTH_TOKEN = os.environ.get("GATEWAY_AUTH_TOKEN", "")
DEFAULT_TZ = os.environ.get("REMINDER_TZ", "America/Sao_Paulo")
MCP_ALLOWED_HOSTS = os.environ.get("MCP_ALLOWED_HOSTS", "")

mcp = FastMCP("reminder")

# FastMCP habilita por padrão uma proteção anti DNS-rebinding que só aceita
# Host localhost/127.0.0.1 — isso bloqueia qualquer domínio público (ex: Railway)
# com "Invalid Host header". Se MCP_ALLOWED_HOSTS não for definido, desligamos
# essa checagem (a rota já é protegida pelo GATEWAY_AUTH_TOKEN quando configurado).
if MCP_ALLOWED_HOSTS:
    hosts = [h.strip() for h in MCP_ALLOWED_HOSTS.split(",") if h.strip()]
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=hosts,
    )
else:
    mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)


def _parse_when(when: str) -> datetime:
    """Aceita datetime ISO 8601, com ou sem timezone. Datas sem timezone são
    interpretadas no fuso configurado em REMINDER_TZ (padrão America/Sao_Paulo)."""
    dt = datetime.fromisoformat(when)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(DEFAULT_TZ))
    return dt.astimezone(ZoneInfo("UTC"))


@mcp.tool()
def create_reminder(message: str, when: str) -> dict:
    """Cria um lembrete que dispara uma notificação Pushover no horário informado.

    Args:
        message: Texto do lembrete a ser enviado na notificação.
        when: Data/hora em formato ISO 8601 (ex: "2026-07-01T09:00:00").
              Se não tiver timezone, é interpretado no fuso configurado
              (padrão America/Sao_Paulo).
    """
    remind_at = _parse_when(when)
    return reminders.create_reminder(message, remind_at)


@mcp.tool()
def list_reminders(include_sent: bool = False) -> list[dict]:
    """Lista os lembretes cadastrados.

    Args:
        include_sent: Se True, inclui lembretes que já foram notificados.
    """
    return reminders.list_reminders(include_sent=include_sent)


@mcp.tool()
def delete_reminder(reminder_id: str) -> dict:
    """Deleta um lembrete pelo seu id.

    Args:
        reminder_id: Id do lembrete (retornado por create_reminder ou list_reminders).
    """
    deleted = reminders.delete_reminder(reminder_id)
    return {"deleted": deleted, "id": reminder_id}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        if GATEWAY_AUTH_TOKEN:
            expected = f"Bearer {GATEWAY_AUTH_TOKEN}"
            if request.headers.get("authorization") != expected:
                return PlainTextResponse("Unauthorized", status_code=401)
        return await call_next(request)


async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "security_enabled": bool(GATEWAY_AUTH_TOKEN)})


@asynccontextmanager
async def lifespan(app: Starlette):
    scheduler.start()
    logger.info("Reminder MCP server iniciado")
    try:
        yield
    finally:
        scheduler.stop()


_sse_app = mcp.sse_app()
routes = list(_sse_app.routes)
routes.append(Route("/health", health_check, methods=["GET"]))

app = Starlette(routes=routes, lifespan=lifespan)
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
