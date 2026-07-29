import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { prisma } from './prisma'
import { sendNotification } from './ntfy'

const DEFAULT_TZ = process.env.REMINDER_TZ || 'America/Sao_Paulo'

let supabaseClient: SupabaseClient | null = null

function getSupabase(): SupabaseClient | null {
  const url = process.env.SUPABASE_URL
  const key = process.env.SUPABASE_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY
  if (url && key) {
    if (!supabaseClient) {
      supabaseClient = createClient(url, key)
    }
    return supabaseClient
  }
  return null
}

export function parseWhen(when: string): Date {
  let date: Date
  if (!when.includes('Z') && !when.includes('+') && !/-\d{2}:\d{2}$/.test(when)) {
    date = new Date(when)
  } else {
    date = new Date(when)
  }

  if (isNaN(date.getTime())) {
    throw new Error(`Data/hora inválida: ${when}`)
  }

  return date
}

export async function createReminder(input: {
  message: string
  when: string
  recorrencia?: number
  recorrenciaIntervalo?: number | null
}) {
  const recorrencia = input.recorrencia ?? 1
  const recorrenciaIntervalo = input.recorrenciaIntervalo ?? null

  if (recorrencia < 1) {
    throw new Error('recorrencia deve ser maior ou igual a 1')
  }

  if (recorrencia > 1 && (!recorrenciaIntervalo || recorrenciaIntervalo <= 0)) {
    throw new Error(
      'recorrenciaIntervalo (em segundos, > 0) é obrigatório quando recorrencia > 1'
    )
  }

  const remindAt = parseWhen(input.when)
  const supabase = getSupabase()

  if (supabase) {
    const { data, error } = await supabase
      .from('reminders')
      .insert({
        message: input.message,
        remind_at: remindAt.toISOString(),
        recorrencia,
        recorrencia_intervalo: recorrenciaIntervalo,
      })
      .select()
      .single()

    if (error) {
      throw new Error(`Erro no Supabase ao criar lembrete: ${error.message}`)
    }

    return {
      id: data.id,
      message: data.message,
      remind_at: data.remind_at,
      created_at: data.created_at,
      sent: data.sent,
      recorrencia: data.recorrencia,
      recorrencia_intervalo: data.recorrencia_intervalo,
      ocorrencias_enviadas: data.ocorrencias_enviadas,
    }
  }

  const reminder = await prisma.reminder.create({
    data: {
      message: input.message,
      remindAt,
      recorrencia,
      recorrenciaIntervalo,
    },
  })

  return {
    id: reminder.id,
    message: reminder.message,
    remind_at: reminder.remindAt.toISOString(),
    created_at: reminder.createdAt.toISOString(),
    sent: reminder.sent,
    recorrencia: reminder.recorrencia,
    recorrencia_intervalo: reminder.recorrenciaIntervalo,
    ocorrencias_enviadas: reminder.ocorrenciasEnviadas,
  }
}

export async function listReminders(includeSent: boolean = false) {
  const supabase = getSupabase()

  if (supabase) {
    let query = supabase.from('reminders').select('*').order('remind_at', { ascending: true })
    if (!includeSent) {
      query = query.eq('sent', false)
    }

    const { data, error } = await query
    if (error) {
      throw new Error(`Erro no Supabase ao listar lembretes: ${error.message}`)
    }

    return (data || []).map((r: any) => ({
      id: r.id,
      message: r.message,
      remind_at: r.remind_at,
      created_at: r.created_at,
      sent: r.sent,
      recorrencia: r.recorrencia,
      recorrencia_intervalo: r.recorrencia_intervalo,
      ocorrencias_enviadas: r.ocorrencias_enviadas,
    }))
  }

  const reminders = await prisma.reminder.findMany({
    where: includeSent ? undefined : { sent: false },
    orderBy: { remindAt: 'asc' },
  })

  return reminders.map((r) => ({
    id: r.id,
    message: r.message,
    remind_at: r.remindAt.toISOString(),
    created_at: r.createdAt.toISOString(),
    sent: r.sent,
    recorrencia: r.recorrencia,
    recorrencia_intervalo: r.recorrenciaIntervalo,
    ocorrencias_enviadas: r.ocorrenciasEnviadas,
  }))
}

export async function deleteReminder(reminderId: string) {
  const supabase = getSupabase()

  if (supabase) {
    const { error } = await supabase.from('reminders').delete().eq('id', reminderId)
    return !error
  }

  try {
    await prisma.reminder.delete({
      where: { id: reminderId },
    })
    return true
  } catch {
    return false
  }
}

export async function processDueReminders() {
  const now = new Date().toISOString()
  const supabase = getSupabase()

  if (supabase) {
    const { data: dueList, error } = await supabase
      .from('reminders')
      .select('*')
      .eq('sent', false)
      .lte('remind_at', now)

    if (error) {
      console.error('[cron] Erro Supabase ao buscar lembretes:', error)
      return []
    }

    const results = []

    for (const reminder of dueList || []) {
      const success = await sendNotification('Lembrete', reminder.message)

      if (success) {
        const novasOcorrencias = (reminder.ocorrencias_enviadas || 0) + 1
        const atingiuLimite = novasOcorrencias >= reminder.recorrencia

        if (atingiuLimite) {
          await supabase
            .from('reminders')
            .update({ sent: true, ocorrencias_enviadas: novasOcorrencias })
            .eq('id', reminder.id)
        } else if (reminder.recorrencia_intervalo) {
          const nextRemindAt = new Date(
            new Date(reminder.remind_at).getTime() + reminder.recorrencia_intervalo * 1000
          ).toISOString()
          await supabase
            .from('reminders')
            .update({ remind_at: nextRemindAt, ocorrencias_enviadas: novasOcorrencias })
            .eq('id', reminder.id)
        }

        results.push({ id: reminder.id, status: 'sent', message: reminder.message })
      } else {
        results.push({ id: reminder.id, status: 'failed', message: reminder.message })
      }
    }

    return results
  }

  const dueList = await prisma.reminder.findMany({
    where: {
      sent: false,
      remindAt: { lte: new Date() },
    },
  })

  const results = []

  for (const reminder of dueList) {
    const success = await sendNotification('Lembrete', reminder.message)

    if (success) {
      const novasOcorrencias = reminder.ocorrenciasEnviadas + 1
      const atingiuLimite = novasOcorrencias >= reminder.recorrencia

      if (atingiuLimite) {
        await prisma.reminder.update({
          where: { id: reminder.id },
          data: {
            sent: true,
            ocorrenciasEnviadas: novasOcorrencias,
          },
        })
      } else if (reminder.recorrenciaIntervalo) {
        const nextRemindAt = new Date(
          reminder.remindAt.getTime() + reminder.recorrenciaIntervalo * 1000
        )
        await prisma.reminder.update({
          where: { id: reminder.id },
          data: {
            remindAt: nextRemindAt,
            ocorrenciasEnviadas: novasOcorrencias,
          },
        })
      }

      results.push({ id: reminder.id, status: 'sent', message: reminder.message })
    } else {
      results.push({ id: reminder.id, status: 'failed', message: reminder.message })
    }
  }

  return results
}
