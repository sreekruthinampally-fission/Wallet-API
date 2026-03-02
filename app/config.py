from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    password_hash_iterations: int = 120_000

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

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value):
        if value is None:
            return "development"
        return str(value).strip().lower()

    @field_validator("jwt_access_token_expire_minutes")
    @classmethod
    def validate_jwt_expiry(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be greater than 0")
        return value

    @field_validator("password_hash_iterations")
    @classmethod
    def validate_hash_iterations(cls, value: int) -> int:
        if value < 100_000:
            raise ValueError("PASSWORD_HASH_ITERATIONS must be at least 100000")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        secret = value.strip()
        if not secret:
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return secret

    @field_validator("debug")
    @classmethod
    def prevent_debug_in_production(cls, value: bool, info):
        environment = (info.data.get("environment") or "development").lower()
        if environment == "production" and value:
            raise ValueError("DEBUG must be false in production")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def enforce_strong_secret_in_production(cls, value: str, info):
        environment = (info.data.get("environment") or "development").lower()
        if environment == "production":
            if value == "change-me-in-env" or len(value) < 32:
                raise ValueError("In production, JWT_SECRET_KEY must be set and at least 32 characters")
        return value


settings = Settings()
