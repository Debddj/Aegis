"""FastAPI dependency injection providers."""

from functools import lru_cache

from backend.config import Settings
from backend.db.session import get_db  # re-export for convenience
from agents.orchestrator import AegisPipeline


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


@lru_cache()
def get_pipeline() -> AegisPipeline:
    """Cached pipeline singleton."""
    return AegisPipeline()
