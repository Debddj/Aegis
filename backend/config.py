"""Application configuration — loaded from .env with sensible defaults."""

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Explicitly load .env file at config load time to support all tools
load_dotenv()


class Settings(BaseSettings):
    # API keys
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    admin_token: str = os.getenv("AEGIS_ADMIN_TOKEN", "aegis-secure-token-2026")

    # Database — SQLite by default for local dev, no Postgres needed
    database_url: str = "sqlite:///./aegis.db"

    # Simulator
    simulator_url: str = "http://localhost:8100"

    # Server ports
    backend_port: int = 8000
    grpc_port: int = 50051

    # Remediation policy
    auto_remediation_enabled: bool = True
    risk_threshold_auto: str = "low"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"  # don't crash on unknown env vars


# Global settings singleton for tools and modules to import directly
settings = Settings()


def get_settings() -> Settings:
    """Factory function for FastAPI dependency injection."""
    return settings
