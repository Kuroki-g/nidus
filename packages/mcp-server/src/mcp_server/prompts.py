from mcp.server.fastmcp import FastMCP


def custom_instruction(name: str, style: str = "friendly") -> str:
    """TODO: Read custom instruction from mounted file"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }
    instruction = styles.get(style, styles["friendly"])
    return f"{instruction} for someone named {name}."


def register_prompts(mcp: FastMCP):
    mcp.prompt()(custom_instruction)
