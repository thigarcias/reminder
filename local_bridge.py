"""Ponte local stdio -> SSE remoto, para conectar um cliente MCP local
(ex: Claude Desktop) ao servidor de lembretes rodando no Railway."""

import asyncio
import sys

import anyio
from mcp.client.sse import sse_client
from mcp.server.stdio import stdio_server

# Ajuste para a URL do seu deploy no Railway
DEFAULT_URL = "https://reminder-mcp.up.railway.app/sse"


async def pipe(source, dest):
    try:
        async for item in source:
            await dest.send(item)
    except Exception:
        pass


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    headers = {}
    token = sys.argv[2] if len(sys.argv) > 2 else None
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with stdio_server() as (local_read, local_write):
        async with sse_client(url, headers=headers) as (remote_read, remote_write):
            async with anyio.create_task_group() as tg:
                tg.start_soon(pipe, local_read, remote_write)
                tg.start_soon(pipe, remote_read, local_write)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
