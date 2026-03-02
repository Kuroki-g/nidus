from mcp.server.fastmcp import FastMCP


def custom_instruction() -> str:
    """Call instruction for this tool"""
    instruction = (
        "NidusMCP is an open-source MCP server that search documents information locally."
        " It provides locally-restricted document search."
        " For database init, update, search, you can use MCP tools."
    )

    return f"{instruction}"


def register_prompts(mcp: FastMCP):
    mcp.prompt()(custom_instruction)
