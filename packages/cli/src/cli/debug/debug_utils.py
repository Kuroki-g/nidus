from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def mcp_connection(url: str):
    """Context manager to manage MCP server connection."""
    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            session.session_id = get_session_id()  # type: ignore[attr-defined]
            yield session
