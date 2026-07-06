"""Database session factory — SQLite with sync engine for simplicity."""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.db.models import Base

logger = logging.getLogger("aegis.db")

# Default to SQLite file in project root
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aegis.db")

# SQLAlchemy engine — connect_args needed for SQLite threading
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized: %s", DATABASE_URL)


def get_db() -> Session:
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
