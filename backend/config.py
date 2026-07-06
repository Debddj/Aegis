"""Application configuration — loaded from .env with sensible defaults."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys
    google_api_key: str = ""
    gemini_api_key: str = ""  # alias used in some .env files

    # Database — SQLite by default for local dev, no Postgres needed
    database_url: str = "sqlite:///./aegis.db"

    # Redis — optional, falls back gracefully
    redis_url: str = ""

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

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


def get_settings() -> Settings:
    """Factory function for dependency injection."""
    return Settings()
