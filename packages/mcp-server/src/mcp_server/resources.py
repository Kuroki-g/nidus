from common.format import format_mes
from mcp.server.fastmcp import FastMCP


def get_single_doc(path: str) -> str:
    """
    get documents from path.
    this method sometimes too strict.
    for rough search, use `list_docs` tool.

    Args:
        keyword (str): keyword to be searched

    Returns:
        str: documents list matched for source name
    """
    try:
        from cli.db.search_db import list_docs_in_db

        results = list_docs_in_db(path)

        if not results:
            return f"source match to {path}' was not found."

        output = []
        for row in results:
            source = row["source"]
            text_snippet = row.get("text", "").replace("\n", " ")[:300]

            output.append(f"--- source: {source} ---\n{text_snippet}...\n")
        return "\n".join(output)
    except Exception as e:
        return format_mes(str(e))


def register_resources(mcp: FastMCP):
    mcp.resource("docs://{name}")(get_single_doc)
