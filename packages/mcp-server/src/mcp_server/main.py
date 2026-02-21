from mcp.server.fastmcp import FastMCP
from . import tools, resources, prompts

def main():
    mcp = FastMCP("NidusMCP", json_response=True)

    # Register all tools, resources, prompts
    tools.register_tools(mcp)
    resources.register_resources(mcp)
    prompts.register_prompts(mcp)

    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
