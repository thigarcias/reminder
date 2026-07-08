# reminder-mcp

Servidor MCP de lembretes: expõe tools para uma LLM criar, listar e deletar
lembretes, e roda em background um agendador que dispara notificações push
via [Pushover](https://pushover.net) no horário programado.

## Tools MCP

- `create_reminder(message: str, when: str, recorrencia: int = 1, recorrencia_intervalo: int | None = None, titulo: str | None = None, prioridade: int = 1)`
  — cria um lembrete. `when` é ISO 8601 (ex: `"2026-07-01T09:00:00"`); sem
  timezone é interpretado no fuso `REMINDER_TZ` (padrão `America/Sao_Paulo`)
  e é o horário da primeira ocorrência. `message` é o corpo da notificação e
  pode ser detalhado (o Pushover aceita até 1024 caracteres). `recorrencia` é
  quantas vezes notificar no total (padrão 1, ou seja, dispara uma única vez).
  `recorrencia_intervalo` é o intervalo em segundos entre cada repetição,
  obrigatório quando `recorrencia > 1` (ex: `3600` para repetir a cada hora,
  `86400` para repetir diariamente). Informar `recorrencia_intervalo` sem também
  definir `recorrencia > 1` é rejeitado (senão o lembrete dispara uma única vez
  e some da lista, mesmo parecendo configurado para repetir). `titulo` é o
  título curto da notificação (padrão `"Lembrete"`). `prioridade` é o nível
  Pushover de `-2` a `2`: `-2` silenciosa, `-1` baixa, `0` normal, `1` alta
  (padrão), `2` emergência (reenvia a cada 60s por até 1h até você confirmar).
- `list_reminders(include_sent: bool = False)` — lista lembretes. Cada item
  inclui `recorrencia`, `recorrencia_intervalo`, `ocorrencias_enviadas`,
  `titulo` e `prioridade`.
- `delete_reminder(reminder_id: str)` — remove um lembrete (cancela também
  as repetições futuras).

Um agendador (`APScheduler`) roda a cada 20s dentro do próprio processo,
verifica lembretes vencidos e envia a notificação Pushover. Se o lembrete
ainda tiver repetições pendentes, ele reagenda `remind_at` somando
`recorrencia_intervalo`; quando a última ocorrência é enviada, marca o
lembrete como concluído.

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
