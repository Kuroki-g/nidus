from mcp.server.fastmcp import FastMCP
from . import tools, resources, prompts

def main():
    mcp = FastMCP("NidusMCP", json_response=True)

    # Register all tools, resources, prompts
    tools.register_tools(mcp)
    resources.register_resources(mcp)
    prompts.register_prompts(mcp)

    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        import sys
        sys.exit(0)

if __name__ == "__main__":
    main()
