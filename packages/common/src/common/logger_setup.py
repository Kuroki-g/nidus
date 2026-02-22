import logging
import sys

from common.config import settings


def setup_logging(level: int = settings.LOG_LEVEL):
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)


if __name__ == "__main__":
    setup_logging()
