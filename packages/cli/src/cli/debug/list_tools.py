import logging

from cli.debug.debug_utils import mcp_connection

logger = logging.getLogger(__name__)


async def list_all_tools(server_url):
    """list all MCP tools"""
    async with mcp_connection(server_url) as session:
        session_id = getattr(session, "session_id", "Unknown")
        logger.info(f"✅ Connected. Session ID: {session_id}")

        result = await session.list_tools()

        print("\n=== Server Tools (Streamable HTTP) ===")
        if not result.tools:
            print("MCP tool was not found.")
            return

        for tool in result.tools:
            print(f"Name       : {tool.name}")
            print(f"Description: {tool.description}")
            print("-" * 30)
