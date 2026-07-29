# reminder-mcp

Servidor MCP de lembretes em **Next.js** preparado para deploy na **Vercel**: expõe ferramentas MCP (`create_reminder`, `list_reminders`, `delete_reminder`) e dispara notificações push via [Ntfy](https://ntfy.sh).

---

## 🚀 Como Funciona

- **MCP Stateless Route (`/api/mcp`)**: Implementado com `@modelcontextprotocol/sdk` usando `WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined })`, garantindo compatibilidade com o modelo serverless stateless da Vercel.
- **Notificações via Ntfy**: As notificações utilizam a API do Ntfy com token de autenticação `NTFY_TOKEN`.
- **Agendamento via Vercel Cron (`/api/cron`)**: O agendador roda a cada 1 minuto através de Vercel Cron Jobs configurados no `vercel.json`.

---

## 🛠️ Ferramentas MCP

1. **`create_reminder(message: str, when: str, recorrencia: int = 1, recorrencia_intervalo: int | None = None)`**
   - Cria um lembrete. `when` é ISO 8601 (ex: `"2026-07-01T09:00:00"`).
   - `recorrencia`: total de ocorrências.
   - `recorrencia_intervalo`: intervalo em segundos entre repetições.
2. **`list_reminders(include_sent: bool = False)`**
   - Lista os lembretes cadastrados.
3. **`delete_reminder(reminder_id: str)`**
   - Deleta um lembrete pelo ID.

---

## 💻 Rodando Localmente

1. Instalar dependências Node.js:
   ```bash
   npm install
   ```

2. Configurar banco local (Prisma / SQLite):
   ```bash
   npx prisma db push
   ```

3. Iniciar o servidor de desenvolvimento:
   ```bash
   npm run dev
   ```
   O servidor estará disponível em `http://localhost:3000`.

---

## ☁️ Deploy na Vercel

1. Suba o projeto para um repositório GitHub / GitLab / Bitbucket.
2. Importe o projeto no painel da **Vercel**.
3. Configure as variáveis de ambiente na Vercel:
   - `NTFY_SERVER_URL`: `https://ntfy.sh`
   - `NTFY_TOPIC`: seu tópico (ex: `reminders`)
   - `NTFY_TOKEN`: seu token do Ntfy (`tk_cg50zt2sueibh16jydupdlxkurd1g`)
   - `DATABASE_URL`: URL do seu banco de dados (ex: Vercel Postgres, Supabase, Neon ou Turso)
   - `CRON_SECRET` *(opcional)*: segredo para proteger a rota `/api/cron`
4. A Vercel executará automaticamente a build (`prisma generate && next build`) e ativará o Cron Job a cada minuto.

---

## 🔌 Conectando um cliente MCP local (Claude Desktop / Cursor)

Use o script `local_bridge.py`:

```bash
python local_bridge.py https://SEU-APP.vercel.app/api/mcp SEU_GATEWAY_AUTH_TOKEN
```
