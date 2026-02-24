import logging


def format_mes(mes: str, log_level: int = logging.ERROR):
    """
    format message.

    Args:
        mes (str): message
        log_level (int): level added to formatted string

    Returns:
        t: d
    """
    level = logging.getLevelName(log_level)

    return f"[{level}] {mes}"
