from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuration settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Onyx application settings
    base_url: str = Field(
        default="http://localhost:3000",
        description="Base URL for the Onyx frontend",
    )
    admin_email: str = Field(
        default="a@example.com",
        description="Admin user email for authentication",
    )
    admin_password: str = Field(
        default="a",
        description="Admin user password for authentication",
    )

    # Browser settings
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode",
    )
    browser: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium",
        description="Browser to use for testing",
    )
    timeout: int = Field(
        default=60000,
        description="Default timeout for operations (ms)",
    )
    expect_timeout: int = Field(
        default=15000,
        description="Default timeout for expect operations (ms)",
    )

    # Directory settings
    reports_dir: str = Field(
        default="./reports",
        description="Directory for test reports and artifacts",
    )

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get the current settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
