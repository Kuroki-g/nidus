import asyncio
import argparse
from contextlib import asynccontextmanager
import logging
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def mcp_connection(url: str):
    """MCPサーバーへの接続・初期化・終了を管理するコンテキストマネージャ"""
    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            setattr(session, "session_id", get_session_id())
            yield session


async def list_all_tools(server_url):
    """list all MCP tools"""
    async with mcp_connection(server_url) as session:
        session_id = getattr(session, "session_id", "Unknown")
        logger.info(f"✅ Connected. Session ID: {session_id}")

        result = await session.list_tools()

        print("\n=== Server Tools (Streamable HTTP) ===")
        if not result.tools:
            print("ツールが見つかりませんでした。")
            return

        for tool in result.tools:
            print(f"Name       : {tool.name}")
            print(f"Description: {tool.description}")
            print("-" * 30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP List Tools (Streamable HTTP)")
    parser.add_argument("--url", default="http://localhost:8000/mcp", help="Server URL")

    args = parser.parse_args()

    try:
        asyncio.run(list_all_tools(args.url))
    except KeyboardInterrupt:
        print("\nAborted by user.")
    except Exception as e:
        print(f"Error: {e}")
