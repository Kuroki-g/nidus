import logging
from pathlib import Path

from platformdirs import user_cache_dir
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "nidus"
    APP_CACHE_DIR: Path = Path(user_cache_dir(APP_NAME)).resolve()
    DB_PATH: Path = APP_CACHE_DIR / ".lancedb"
    TABLE_NAME: str = "docs"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    LOG_LEVEL: int = logging.INFO
    SEARCH_LIMIT: int = 5

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
