from mcp.server.fastmcp import FastMCP
from common.lance_db_manager import LanceDBManager
from . import tools, resources, prompts
from common.config import settings


def main():
    mcp = FastMCP(
        "NidusMCP", json_response=True, host=settings.HOST, port=settings.PORT
    )

    # Register all tools, resources, prompts
    tools.register_tools(mcp)
    resources.register_resources(mcp)
    prompts.register_prompts(mcp)

    # init db connection
    LanceDBManager()

    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        import sys

        sys.exit(0)


if __name__ == "__main__":
    main()
