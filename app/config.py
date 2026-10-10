"""Application configuration management using Pydantic Settings.

Loads environment variables from .env file or system environment with
validation and type safety.
"""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema and environment variable loader."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Information
    APP_NAME: str = "AI-Powered Task Management System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="Current environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode flag")
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/task_management",
        description="SQLAlchemy database connection URL",
    )

    # JWT Authentication Configuration
    JWT_SECRET_KEY: str = Field(
        default="replace_with_a_secure_random_secret_at_least_32_characters_long",
        description="Secret key for signing and verifying JWT tokens",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Token expiration duration in minutes",
    )

    # Google Gemini AI Integration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key from Google AI Studio",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Configured Gemini model identifier",
    )

    # Seed User Configuration
    SEED_ADMIN_EMAIL: str = "admin@taskflow.dev"
    SEED_ADMIN_PASSWORD: str = "AdminPass123!"
    SEED_USER_EMAIL: str = "user@taskflow.dev"
    SEED_USER_PASSWORD: str = "UserPass123!"

    @property
    def is_ai_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())


@lru_cache()
def get_settings() -> Settings:
    """Return cached instance of application settings."""
    return Settings()


settings = get_settings()
