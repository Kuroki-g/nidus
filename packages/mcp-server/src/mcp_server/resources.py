from mcp.server.fastmcp import FastMCP

def get_docs(name: str) -> str:
    return f"Doc: {name}!"

def register_resources(mcp: FastMCP):
    mcp.resource("docs://{name}")(get_docs)
