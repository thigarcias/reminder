import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Reminder MCP Server',
  description: 'Servidor MCP de Lembretes rodando na Vercel',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  )
}
