"""FastAPI dependency injection providers."""

from functools import lru_cache

from agents.orchestrator import AegisPipeline
from backend.config import Settings


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


@lru_cache()
def get_pipeline() -> AegisPipeline:
    """Cached pipeline singleton."""
    return AegisPipeline()
