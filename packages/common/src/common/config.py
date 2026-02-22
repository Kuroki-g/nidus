import logging

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_PATH: str = "./.lancedb"
    TABLE_NAME: str = "docs"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    LOG_LEVEL: int = logging.INFO

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


settings = Settings()
