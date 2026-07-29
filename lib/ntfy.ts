/**
 * Envio de notificações via Ntfy (https://ntfy.sh).
 */

const DEFAULT_SERVER_URL = 'https://ntfy.sh'
const DEFAULT_TOPIC = 'reminders'
const DEFAULT_DEV_TOKEN = 'tk_cg50zt2sueibh16jydupdlxkurd1g'

export async function sendNotification(title: string, message: string): Promise<boolean> {
  const serverUrl = (process.env.NTFY_SERVER_URL || DEFAULT_SERVER_URL).replace(/\/$/, '')
  const topic = process.env.NTFY_TOPIC || DEFAULT_TOPIC
  const token = process.env.NTFY_TOKEN || DEFAULT_DEV_TOKEN

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
    const response = await fetch(serverUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    })

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
