import logging
import time
from pathlib import Path

from watchdog.events import FileMovedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class _NidusEventHandler(FileSystemEventHandler):
    def __init__(self, supported_extensions: frozenset[str]) -> None:
        self._extensions = supported_extensions

    def _is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in self._extensions

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._is_supported(event.src_path):
            return
        logger.info(f"[watch] created: {event.src_path}")
        _add([Path(event.src_path)])

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._is_supported(event.src_path):
            return
        logger.info(f"[watch] modified: {event.src_path}")
        _add([Path(event.src_path)])

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._is_supported(event.src_path):
            return
        logger.info(f"[watch] deleted: {event.src_path}")
        _delete([Path(event.src_path)])

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            logger.info(f"[watch] moved (delete old): {event.src_path}")
            _delete([Path(event.src_path)])
        if self._is_supported(event.dest_path):
            logger.info(f"[watch] moved (add new): {event.dest_path}")
            _add([Path(event.dest_path)])


def _add(paths: list[Path]) -> None:
    try:
        from cli.db.update_db import update_files_in_db

        update_files_in_db(paths)
    except Exception as e:
        logger.error(f"[watch] add failed: {e}")


def _delete(paths: list[Path]) -> None:
    try:
        from cli.db.delete_db_record import delete_files_in_db

        delete_files_in_db(paths)
    except Exception as e:
        logger.error(f"[watch] delete failed: {e}")


def watch_directories(dirs: list[Path], recursive: bool = True) -> None:
    """Start watching directories and block until interrupted."""
    from cli.processor.file_processor import CHUNK_STRATEGIES

    handler = _NidusEventHandler(frozenset(CHUNK_STRATEGIES.keys()))
    observer = Observer()
    for d in dirs:
        observer.schedule(handler, str(d), recursive=recursive)
        logger.info(f"[watch] watching: {d}")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
