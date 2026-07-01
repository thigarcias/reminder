# reminder-mcp

Servidor MCP de lembretes: expõe tools para uma LLM criar, listar e deletar
lembretes, e roda em background um agendador que dispara notificações push
via [Pushover](https://pushover.net) no horário programado.

## Tools MCP

- `create_reminder(message: str, when: str)` — cria um lembrete. `when` é
  ISO 8601 (ex: `"2026-07-01T09:00:00"`); sem timezone é interpretado no
  fuso `REMINDER_TZ` (padrão `America/Sao_Paulo`).
- `list_reminders(include_sent: bool = False)` — lista lembretes.
- `delete_reminder(reminder_id: str)` — remove um lembrete.

Um agendador (`APScheduler`) roda a cada 20s dentro do próprio processo,
verifica lembretes vencidos e envia a notificação Pushover.

## Rodando localmente

```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt       # Linux/Mac

cp .env.example .env   # ajuste as chaves do Pushover se necessário
./.venv/Scripts/python -m uvicorn gateway:app --host 0.0.0.0 --port 8000
```

Endpoints: `GET /health`, `GET /sse` (conexão MCP), `POST /messages` (mensagens MCP).

## Deploy no Railway

O `Dockerfile` já está pronto para build automático no Railway (mesmo padrão
usado no projeto `scrapper`). Variáveis de ambiente a configurar no Railway:

- `PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN` — credenciais do Pushover.
- `GATEWAY_AUTH_TOKEN` — token opcional; se definido, exige
  `Authorization: Bearer <token>` em todas as rotas exceto `/health`.
- `REMINDER_TZ` — fuso horário padrão para `when` sem timezone.
- `REMINDER_DB_PATH` — caminho do SQLite. Configure um Railway Volume
  montado em `/data` e use `REMINDER_DB_PATH=/data/reminders.db` para os
  lembretes persistirem entre deploys.

## Conectando um cliente MCP local (ex: Claude Desktop)

Use `local_bridge.py` para fazer a ponte stdio ↔ SSE remoto:

```bash
python local_bridge.py https://SEU-APP.up.railway.app/sse SEU_GATEWAY_AUTH_TOKEN
```
