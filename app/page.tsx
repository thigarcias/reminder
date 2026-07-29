export default function HomePage() {
  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Reminder MCP Server</h1>
      <p>Servidor MCP de Lembretes rodando na Vercel.</p>
      <ul>
        <li><strong>MCP Endpoint:</strong> <code>/api/mcp</code></li>
        <li><strong>Cron Endpoint:</strong> <code>/api/cron</code></li>
      </ul>
    </main>
  )
}
