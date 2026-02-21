from mcp.server.fastmcp import FastMCP

def search_docs(keyword: str) -> str:
    """TODO: Search by keyword"""
    return f"Searching for: {keyword}"

def register_tools(mcp: FastMCP):
    mcp.tool()(search_docs)
