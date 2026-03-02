from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Wallet API"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://wallet:wallet@localhost:5432/wallet_db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "on", "debug", "development", "dev"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "release", "production", "prod"}:
            return False
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value):
        if value is None:
            return "INFO"
        return str(value).strip().upper()


settings = Settings()
