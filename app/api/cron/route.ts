import { NextResponse } from 'next/server'
import { processDueReminders } from '@/lib/reminders'

export async function GET(request: Request) {
  const authHeader = request.headers.get('authorization')
  const cronSecret = process.env.CRON_SECRET

  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const results = await processDueReminders()
    return NextResponse.json({
      success: true,
      processed: results.length,
      details: results,
    })
  } catch (error) {
    console.error('[cron] Error processing due reminders:', error)
    return NextResponse.json(
      { error: 'Internal Server Error', details: String(error) },
      { status: 500 }
    )
  }
}
