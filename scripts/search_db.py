import asyncio
from mcp_server.tools import search_docs 

async def debug_tool():
    try:
        result = search_docs(keyword="test-keyword")
        print(f"関数の戻り値: {result}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    asyncio.run(debug_tool())