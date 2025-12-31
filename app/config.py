"""
Configuration module for Pastebin Lite.
Loads environment variables and provides config objects.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    APP_DOMAIN: str = os.getenv("APP_DOMAIN", "http://localhost:8000")
    TEST_MODE: bool = os.getenv("TEST_MODE", "0").lower() in ("true", "1", "yes")

    class Config:
        """Pydantic config."""
        case_sensitive = True


settings = Settings()
