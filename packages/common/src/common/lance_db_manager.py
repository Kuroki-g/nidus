import threading

import lancedb


class LanceDBManager:
    _instance = None
    _db = None
    _lock = threading.Lock()

    def __new__(cls, db_uri: str = "data/lancedb"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LanceDBManager, cls).__new__(cls)
                    cls._instance._db = lancedb.connect(db_uri)
                    print(f"Connected to LanceDB at: {db_uri}")
        return cls._instance

    @property
    def db(self) -> lancedb.DBConnection:
        return self._db


def get_db():
    manager = LanceDBManager()
    print(f"Thread {threading.current_thread().name}: {id(manager)}")
