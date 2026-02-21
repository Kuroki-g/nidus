"""
FastMCP quickstart example.

Run from the repository root:
    uv run examples/snippets/servers/fastmcp_quickstart.py
"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("NidusMCP", json_response=True)

# Add an addition tool
@mcp.tool()
def search_docs(keyword: str) -> int:
    """TODO: Search by keyword"""
    return keyword

@mcp.resource("docs://{name}")
def get_docs(name: str) -> str:
    """TODO: Get document from mounted docs directory"""
    return f"Doc: {name}!"

# Add a prompt
@mcp.prompt()
def custom_instruction(name: str, style: str = "friendly") -> str:
    """TODO: Read custom instruction from mounted file"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."

def main():
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
