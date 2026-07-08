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
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

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
def create_reminder(
    message: str,
    when: str,
    recorrencia: int = 1,
    recorrencia_intervalo: int | None = None,
    titulo: str | None = None,
    prioridade: int = 1,
) -> dict:
    """Cria um lembrete que dispara uma notificação Pushover no horário informado.

    Args:
        message: Texto do lembrete a ser enviado na notificação. É o corpo da
              mensagem e pode ser detalhado (o Pushover aceita até 1024 chars).
        when: Data/hora em formato ISO 8601 (ex: "2026-07-01T09:00:00").
              Se não tiver timezone, é interpretado no fuso configurado
              (padrão America/Sao_Paulo). É o horário da primeira ocorrência.
        recorrencia: Quantas vezes notificar no total. Padrão 1 (dispara uma
              única vez e não se repete).
        recorrencia_intervalo: Intervalo em segundos entre cada repetição.
              Obrigatório quando recorrencia > 1 (ex: 3600 para repetir a
              cada hora, 86400 para repetir diariamente).
        titulo: Título curto da notificação (aparece em negrito acima da
              mensagem). Opcional; se omitido, usa "Lembrete".
        prioridade: Nível de prioridade da notificação no Pushover, de -2 a 2:
              -2 = silenciosa (sem som/vibração), -1 = baixa (sem som),
              0 = normal, 1 = alta (padrão, sempre com som), 2 = emergência
              (repete até você confirmar). Padrão 1.
    """
    if recorrencia < 1:
        raise ValueError("recorrencia deve ser maior ou igual a 1")
    if recorrencia > 1 and (not recorrencia_intervalo or recorrencia_intervalo <= 0):
        raise ValueError(
            "recorrencia_intervalo (em segundos, > 0) é obrigatório quando recorrencia > 1"
        )
    if recorrencia == 1 and recorrencia_intervalo:
        raise ValueError(
            "recorrencia_intervalo foi informado mas recorrencia é 1 (padrão); "
            "defina recorrencia > 1 para o lembrete realmente se repetir, "
            "senão ele é enviado uma única vez e some da lista"
        )
    if prioridade < -2 or prioridade > 2:
        raise ValueError("prioridade deve estar entre -2 e 2 (padrão Pushover)")
    remind_at = _parse_when(when)
    return reminders.create_reminder(
        message,
        remind_at,
        recorrencia=recorrencia,
        recorrencia_intervalo=recorrencia_intervalo,
        titulo=titulo,
        prioridade=prioridade,
    )


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


class AuthMiddleware:
    """Middleware ASGI puro (não usa BaseHTTPMiddleware, que quebra os
    endpoints crus de streaming do transporte SSE do MCP com
    'AssertionError: Unexpected message')."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not GATEWAY_AUTH_TOKEN or scope.get("path") == "/health":
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers", []))
        auth_val = headers.get(b"authorization", b"").decode("latin-1")
        if auth_val != f"Bearer {GATEWAY_AUTH_TOKEN}":
            response = PlainTextResponse("Unauthorized", status_code=401)
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)


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
