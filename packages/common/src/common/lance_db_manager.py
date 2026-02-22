import logging
import threading

from common.config import settings

import lancedb

logger = logging.getLogger(__name__)


class LanceDBManager:
    _instance = None
    _db = None
    _lock = threading.Lock()

    def __new__(cls, db_uri: str = settings.DB_PATH):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LanceDBManager, cls).__new__(cls)
                    cls._instance._db = lancedb.connect(db_uri)
                    logger.info(f"Connected to LanceDB at: {db_uri}")
        return cls._instance

    @property
    def db(self) -> lancedb.DBConnection:
        return self._db


def get_db():
    manager = LanceDBManager()
    logger.info(f"Thread {threading.current_thread().name}: {id(manager)}")
