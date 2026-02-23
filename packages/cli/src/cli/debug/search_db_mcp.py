import logging

from cli.debug.debug_utils import mcp_connection
from mcp.types import CallToolResult, TextContent

logger = logging.getLogger(__name__)


def print_ui(keyword: str, response: CallToolResult):
    print("\n" + "━" * 50)
    print(f" 🔍 SEARCH RESULT: '{keyword}'")
    print("━" * 50)

    if not response.content:
        print("   (No matching documents found)")
    else:
        for i, content in enumerate(response.content, 1):
            if isinstance(content, TextContent):
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
