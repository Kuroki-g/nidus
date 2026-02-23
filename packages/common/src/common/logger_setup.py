import logging
import sys

LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(message)s"
formatter = logging.Formatter(LOG_FORMAT)


def setup_logging(level="INFO"):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Clear existing handler
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    # override uvicorn logger config
    try:
        from uvicorn.config import LOGGING_CONFIG

        LOGGING_CONFIG["formatters"]["default"]["fmt"] = LOG_FORMAT
        LOGGING_CONFIG["formatters"]["access"]["fmt"] = LOG_FORMAT
        for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            u_logger = logging.getLogger(name)
            u_logger.handlers = []
            u_logger.propagate = True

    except ImportError:
        pass

    silence_loggers = ["sentence_transformers", "torch", "httpx"]
    for name in silence_loggers:
        tgt = logging.getLogger(name)
        tgt.setLevel(logging.WARNING)
        tgt.propagate = True
        tgt.handlers = []
