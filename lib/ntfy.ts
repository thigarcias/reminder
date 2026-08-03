/**
 * Envio de notificações via Ntfy (https://ntfy.sh).
 */

const DEFAULT_SERVER_URL = 'https://ntfy.sh'
const DEFAULT_TOPIC = 'reminders'

export async function sendNotification(title: string, message: string): Promise<boolean> {
  const serverUrl = (process.env.NTFY_SERVER_URL || DEFAULT_SERVER_URL).replace(/\/$/, '')
  const topic = process.env.NTFY_TOPIC || DEFAULT_TOPIC
  const token = process.env.NTFY_TOKEN

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const payload = {
      topic,
      title: title.slice(0, 250),
      message,
      priority: 3,
      tags: ['alarm', 'reminder'],
    }

    // Publicando via JSON POST no endpoint raiz do Ntfy (https://ntfy.sh/)
    let response = await fetch(serverUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    })

    // Se falhar com 401 e foi enviado token de autorização, tenta novamente sem a header de autorização
    if (response.status === 401 && headers['Authorization']) {
      console.warn('[ntfy] Token de autorização recusado (401). Tentando enviar sem token...')
      delete headers['Authorization']
      response = await fetch(serverUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      })
    }

    if (!response.ok) {
      const errText = await response.text().catch(() => '')
      console.error(`[ntfy] HTTP error ${response.status}: ${errText}`)
      return false
    }

    return true
  } catch (error) {
    console.error('[ntfy] Error sending notification:', error)
    return false
  }
}

