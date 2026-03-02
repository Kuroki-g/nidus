import logging

from common.config import settings
from common.logger_setup import setup_logging
from mcp.server.fastmcp import FastMCP


def main():
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)

    logger.info("Nidus MCP: Document search server")
    mcp = FastMCP(
        "NidusMCP",
        instructions=(
            "Nidus is a knowledge base server."
            "User can put documents (planning document, document, manual etc.)"
            "Nidus store separate files into chunks and store as a vector."
        ),
        json_response=True,
        host=settings.HOST,
        port=settings.PORT,
    )

    logger.debug("Registering all tools, resources, prompts")
    from mcp_server import prompts, resources, tools

    tools.register_tools(mcp)
    resources.register_resources(mcp)
    prompts.register_prompts(mcp)

    from common.lance_db_manager import LanceDBManager

    LanceDBManager()

    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        import sys

        sys.exit(0)


if __name__ == "__main__":
    main()
