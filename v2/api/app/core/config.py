from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", validation_alias="LALAGOLF_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://lalagolf:lalagolf@localhost:5432/lalagolf_v2",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY")
    session_cookie_name: str = Field(
        default="lalagolf_session",
        validation_alias="SESSION_COOKIE_NAME",
    )
    session_cookie_secure: bool = Field(default=False, validation_alias="SESSION_COOKIE_SECURE")
    session_lifetime_days: int = Field(default=30, validation_alias="SESSION_LIFETIME_DAYS")
    request_id_header: str = Field(default="X-Request-ID", validation_alias="REQUEST_ID_HEADER")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    upload_storage_dir: str = Field(
        default="storage/uploads",
        validation_alias="UPLOAD_STORAGE_DIR",
    )
    upload_max_bytes: int = Field(default=1_000_000, validation_alias="UPLOAD_MAX_BYTES")
    cors_origins: str = Field(
        default="http://localhost:2323,http://127.0.0.1:2323",
        validation_alias="CORS_ORIGINS",
    )
    web_base_url: str = Field(default="http://localhost:2323", validation_alias="WEB_BASE_URL")
    google_oauth_client_id: str | None = Field(
        default=None,
        validation_alias="GOOGLE_OAUTH_CLIENT_ID",
    )
    google_oauth_client_secret: str | None = Field(
        default=None,
        validation_alias="GOOGLE_OAUTH_CLIENT_SECRET",
    )
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:2324/api/v1/auth/google/callback",
        validation_alias="GOOGLE_OAUTH_REDIRECT_URI",
    )
    google_oauth_state_cookie_name: str = Field(
        default="golfraiders_google_oauth_state",
        validation_alias="GOOGLE_OAUTH_STATE_COOKIE_NAME",
    )
    ollama_enabled: bool = Field(default=False, validation_alias="OLLAMA_ENABLED")
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(default="llama3.1", validation_alias="OLLAMA_MODEL")
    ollama_timeout_seconds: float = Field(default=5.0, validation_alias="OLLAMA_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
