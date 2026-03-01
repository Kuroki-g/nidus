import logging
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_cache_dir(app_name: str) -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / app_name


class Settings(BaseSettings):
    APP_NAME: str = "nidus"
    APP_CACHE_DIR: Path = _default_cache_dir(APP_NAME)
    DB_PATH: Path = APP_CACHE_DIR / ".lancedb"
    TABLE_NAME: str = "docs"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    LOG_LEVEL: int = logging.INFO
    SEARCH_LIMIT: int = 5
    SEARCH_RRF_K: int = 60
    SEARCH_ADJACENT_WINDOW: int = 1

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
