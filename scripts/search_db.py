import asyncio
import argparse
import logging
from contextlib import asynccontextmanager

from mcp import ClientSession, types
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


def print_ui(keyword: str, response: types.CallToolResult):
    print("\n" + "━" * 50)
    print(f" 🔍 SEARCH RESULT: '{keyword}'")
    print("━" * 50)

    if not response.content:
        print("   (No matching documents found)")
    else:
        for i, content in enumerate(response.content, 1):
            if isinstance(content, types.TextContent):
                text = content.text.strip()
                print(f" [{i}] {text}")
    print("━" * 50 + "\n")


async def run_search(keyword: str, server_url: str):
    try:
        async with mcp_connection(server_url) as session:
            session_id = getattr(session, "session_id", "Unknown")
            logger.info(f"✅ Connected. Session ID: {session_id}")
            logger.info(f"Calling 'search_docs' with keyword: {keyword}")
            result = await session.call_tool(
                "search_docs", arguments={"keyword": keyword}
            )
            print_ui(keyword, result)

    except Exception as e:
        logger.error(f"❌ Execution failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Search Client")
    parser.add_argument("keyword", nargs="?", default="test", help="Search keyword")
    parser.add_argument("--url", default="http://localhost:8000/mcp", help="Server URL")

    args = parser.parse_args()

    try:
        asyncio.run(run_search(args.keyword, args.url))
    except KeyboardInterrupt:
        print("\nAborted by user.")
