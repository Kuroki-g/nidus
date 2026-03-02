import logging
import threading
from pathlib import Path

import lancedb

from common.config import settings

logger = logging.getLogger(__name__)


class LanceDBManager:
    _instance: LanceDBManager | None = None
    _db: lancedb.DBConnection | None = None
    _db_uri: str | None = None
    _lock = threading.Lock()

    def __new__(cls, db_uri: str | Path = settings.DB_PATH) -> LanceDBManager:
        db_uri_str = str(db_uri)
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._db = lancedb.connect(db_uri_str)
                    cls._db_uri = db_uri_str
                    logger.info(f"Connected to LanceDB at: {db_uri_str}")
        return cls._instance

    @property
    def db(self) -> lancedb.DBConnection:
        assert self._db is not None
        return self._db

    @property
    def db_uri(self) -> str:
        assert self._db_uri is not None
        return self._db_uri


def get_db():
    manager = LanceDBManager()
    logger.info(f"Thread {threading.current_thread().name}: {id(manager)}")
