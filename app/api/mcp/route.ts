import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { WebStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js'
import { z } from 'zod'
import { createReminder, listReminders, deleteReminder } from '@/lib/reminders'

function createMcpServer() {
  const server = new McpServer({
    name: 'reminder',
    version: '1.0.0',
  })

  server.tool(
    'create_reminder',
    'Cria um lembrete que dispara uma notificação Ntfy no horário informado.',
    {
      message: z.string().describe('Texto do lembrete a ser enviado na notificação.'),
      when: z.string().describe('Data/hora em formato ISO 8601 (ex: "2026-07-01T09:00:00").'),
      recorrencia: z.number().int().min(1).default(1).describe('Quantas vezes notificar no total. Padrão 1.'),
      recorrencia_intervalo: z
        .number()
        .int()
        .positive()
        .optional()
        .describe('Intervalo em segundos entre cada repetição. Obrigatório quando recorrencia > 1.'),
    },
    async ({ message, when, recorrencia, recorrencia_intervalo }) => {
      const result = await createReminder({
        message,
        when,
        recorrencia,
        recorrenciaIntervalo: recorrencia_intervalo,
      })
      return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] }
    }
  )

  server.tool(
    'list_reminders',
    'Lista os lembretes cadastrados.',
    {
      include_sent: z.boolean().default(false).describe('Se true, inclui lembretes que já foram notificados.'),
    },
    async ({ include_sent }) => {
      const result = await listReminders(include_sent)
      return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] }
    }
  )

  server.tool(
    'delete_reminder',
    'Deleta um lembrete pelo seu id.',
    {
      reminder_id: z.string().describe('Id do lembrete (retornado por create_reminder ou list_reminders).'),
    },
    async ({ reminder_id }) => {
      const deleted = await deleteReminder(reminder_id)
      return { content: [{ type: 'text' as const, text: JSON.stringify({ deleted, id: reminder_id }, null, 2) }] }
    }
  )

  return server
}

async function handler(request: Request): Promise<Response> {
  const token = process.env.GATEWAY_AUTH_TOKEN
  if (token) {
    const authHeader = request.headers.get('authorization')
    if (authHeader !== `Bearer ${token}`) {
      return new Response('Unauthorized', { status: 401 })
    }
  }

  const server = createMcpServer()
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // stateless — necessário para Vercel serverless
  })

  await server.connect(transport)
  return transport.handleRequest(request)
}

export const GET = handler
export const POST = handler
export const DELETE = handler
