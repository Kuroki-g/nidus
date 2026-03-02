import logging
import threading
from pathlib import Path

import lancedb

from common.config import settings

logger = logging.getLogger(__name__)


class LanceDBManager:
    _instance = None
    _db = None
    _db_uri = None
    _lock = threading.Lock()

    def __new__(cls, db_uri: str = settings.DB_PATH):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._db = lancedb.connect(db_uri)
                    cls._db_uri = db_uri
                    logger.info(f"Connected to LanceDB at: {db_uri}")
        return cls._instance

    @property
    def db(self) -> lancedb.DBConnection:
        return self._db

    @property
    def db_uri(self) -> Path:
        return self._db_uri


def get_db():
    manager = LanceDBManager()
    logger.info(f"Thread {threading.current_thread().name}: {id(manager)}")
