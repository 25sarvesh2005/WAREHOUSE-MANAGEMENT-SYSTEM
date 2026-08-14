"""
--------------------------------------------------------------------------------
File        : core/config/settings.py
Purpose     : Load typed runtime settings from environment variables.

Responsibilities:
    - Define safe defaults for local development.
    - Expose cached application settings to backend modules.

Flow:
    Environment variables
        ->
    Settings()
        ->
    get_settings()

Used By:
    - main.py
    - common/logger.py
    - core/database/database.py

Returns:
    get_settings() -> Settings - Cached application configuration.

Raises:
    pydantic.ValidationError: When required settings are invalid.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def _normalize_postgresql_url(database_url: str) -> URL:
    """
    Parse and validate a PostgreSQL connection URL.

    Legacy ``postgres://`` URLs are normalized before SQLAlchemy parses them so
    deployment-provided connection strings remain compatible.

    Args:
        database_url: Database URL supplied through application settings.

    Returns:
        URL: Parsed SQLAlchemy PostgreSQL URL.

    Raises:
        ValueError: If the URL is empty or does not target PostgreSQL.
    """
    normalized_url = database_url.strip()
    if not normalized_url:
        raise ValueError("Database URL must not be empty")
    if normalized_url.startswith("postgres://"):
        normalized_url = normalized_url.replace("postgres://", "postgresql://", 1)

    parsed_url = make_url(normalized_url)
    if parsed_url.get_backend_name() != "postgresql":
        raise ValueError("Database URL must use PostgreSQL")
    return parsed_url


def _render_database_url(database_url: URL, driver_name: str) -> str:
    """
    Render a PostgreSQL URL for the requested SQLAlchemy driver.

    SSL query argument names are translated between asyncpg and psycopg without
    exposing the password or changing the supplied host, user, or database.

    Args:
        database_url: Parsed SQLAlchemy database URL.
        driver_name: SQLAlchemy driver name to place in the rendered URL.

    Returns:
        str: Driver-specific database URL with the password preserved.

    Raises:
        ValueError: If an unsupported driver name is requested.
    """
    if driver_name not in {"postgresql+asyncpg", "postgresql+psycopg"}:
        raise ValueError(f"Unsupported PostgreSQL driver: {driver_name}")

    query = dict(database_url.query)
    if driver_name == "postgresql+asyncpg" and "sslmode" in query:
        query.setdefault("ssl", query.pop("sslmode"))
    if driver_name == "postgresql+psycopg" and "ssl" in query:
        query.setdefault("sslmode", query.pop("ssl"))

    rendered_url = database_url.set(drivername=driver_name, query=query)
    return rendered_url.render_as_string(hide_password=False)


class Settings(BaseSettings):
    """
    Typed application settings loaded from environment variables.

    Values are intentionally limited to safe local defaults and deployment
    environments must inject real secrets outside source control.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = Field(
        default="postgresql+asyncpg://warehouse_app:change-me@localhost:5432/warehouse_ops"
    )
    migration_database_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10
    jwt_secret: str = "replace-with-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7
    log_level: str = "INFO"
    frontend_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    ai_enabled: bool = False
    ai_provider: Literal["disabled", "google_genai"] = "disabled"
    ai_model: str = "gemini-3.1-flash-lite-preview"
    ai_log_prompt_excerpts: bool = False
    ai_prompt_excerpt_chars: int = 500
    ai_response_excerpt_chars: int = 2000
    google_genai_api_key: str = ""
    google_api_key: str = ""
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    deepgram_api_key: str = ""
    sarvam_api_key: str = ""
    voice_stt_provider: Literal["deepgram", "sarvam", "disabled"] = "deepgram"
    voice_tts_provider: Literal["sarvam", "disabled"] = "sarvam"
    voice_audio_retention_enabled: bool = False
    voice_max_audio_seconds: int = 30
    voice_max_audio_bytes: int = 5242880
    voice_allowed_mime_types: str = "audio/webm,audio/wav,audio/mpeg,audio/mp4,audio/ogg"
    voice_default_language: str = "en-IN"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001
    mcp_transport: Literal["streamable-http"] = "streamable-http"
    warehouse_api_base_url: str = "http://127.0.0.1:8000"
    bootstrap_admin_email: str = "admin@whitfield.local"
    bootstrap_admin_password: str = "change-this-before-use"
    initialize_schema_on_startup: bool = True

    @property
    def runtime_database_url(self) -> str:
        """
        Return the runtime URL using SQLAlchemy's asyncpg dialect.

        Persistent deployments may use a direct Supabase connection or the
        Supavisor session pooler. Port 6543 transaction pooling is rejected
        because this service is not deployed as a serverless workload.

        Returns:
            str: PostgreSQL URL rendered with the asyncpg driver.

        Raises:
            ValueError: If the URL is not PostgreSQL or uses transaction pooling.
        """
        parsed_url = _normalize_postgresql_url(self.database_url)
        if parsed_url.port == 6543:
            raise ValueError(
                "DATABASE_URL uses port 6543 transaction pooling; use a direct "
                "Supabase connection or Supavisor session mode on port 5432"
            )
        return _render_database_url(parsed_url, "postgresql+asyncpg")

    @property
    def alembic_database_url(self) -> str:
        """
        Return the synchronous psycopg URL used by Alembic.

        ``MIGRATION_DATABASE_URL`` takes precedence so migrations can use the
        direct Supabase connection while runtime optionally uses session pooling.

        Returns:
            str: PostgreSQL URL rendered with the psycopg driver.

        Raises:
            ValueError: If the selected URL is not a PostgreSQL URL.
        """
        source_url = self.migration_database_url or self.database_url
        parsed_url = _normalize_postgresql_url(source_url)
        return _render_database_url(parsed_url, "postgresql+psycopg")

    @property
    def cors_origins(self) -> list[str]:
        """
        Return configured frontend origins as a list.

        The comma-separated environment value is trimmed and empty entries are
        discarded before being passed to CORS middleware.

        Returns:
            list[str]: Allowed frontend origins.

        Raises:
            None.
        """
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings object.

    Caching keeps environment parsing deterministic during normal application
    runtime while still allowing tests to clear the cache when needed.

    Returns:
        Settings: Loaded settings.

    Raises:
        pydantic.ValidationError: When environment values fail validation.
    """
    return Settings()


def validate_production_configuration(settings: Settings) -> list[str]:
    """
    Validate application settings against production hardening requirements.

    Args:
        settings: Application settings to validate.

    Returns:
        list[str]: Warning messages for non-production environments.

    Raises:
        ValueError: If production environment has insecure credentials or configuration.
    """
    warnings: list[str] = []
    is_prod = settings.app_env == "production"

    # 1. JWT Secret strength
    insecure_jwt_secrets = {
        "replace-with-long-random-secret",
        "secret",
        "changeme",
        "change-me",
        "test",
    }
    if len(settings.jwt_secret) < 32 or settings.jwt_secret in insecure_jwt_secrets:
        msg = "JWT_SECRET is weak or uses a default placeholder (minimum 32 characters recommended)."
        if is_prod:
            raise ValueError(f"CRITICAL PRODUCTION CONFIGURATION ERROR: {msg}")
        warnings.append(msg)

    # 2. Bootstrap Admin Password
    insecure_passwords = {
        "change-this-before-use",
        "admin",
        "password",
        "WhitfieldAdmin123!",
        "12345678",
    }
    if settings.bootstrap_admin_password in insecure_passwords:
        msg = "BOOTSTRAP_ADMIN_PASSWORD uses a well-known default value."
        if is_prod:
            raise ValueError(f"CRITICAL PRODUCTION CONFIGURATION ERROR: {msg}")
        warnings.append(msg)

    # 3. AI configuration
    if settings.ai_enabled and settings.ai_provider == "google_genai":
        has_key = bool(settings.google_genai_api_key.strip() or settings.google_api_key.strip())
        if not has_key:
            msg = "AI is enabled with google_genai provider, but no GOOGLE_GENAI_API_KEY is configured."
            if is_prod:
                raise ValueError(f"CRITICAL PRODUCTION CONFIGURATION ERROR: {msg}")
            warnings.append(msg)

    # 4. Voice configuration
    if settings.voice_stt_provider == "deepgram" and not settings.deepgram_api_key.strip():
        msg = "VOICE_STT_PROVIDER is set to deepgram, but no DEEPGRAM_API_KEY is configured."
        if is_prod:
            raise ValueError(f"CRITICAL PRODUCTION CONFIGURATION ERROR: {msg}")
        warnings.append(msg)

    if settings.voice_tts_provider == "sarvam" and not settings.sarvam_api_key.strip():
        msg = "VOICE_TTS_PROVIDER is set to sarvam, but no SARVAM_API_KEY is configured."
        if is_prod:
            raise ValueError(f"CRITICAL PRODUCTION CONFIGURATION ERROR: {msg}")
        warnings.append(msg)

    return warnings
