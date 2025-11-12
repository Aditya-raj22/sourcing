"""
Database initialization and session management.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config import config
from src.models import Base
import logging

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    echo=config.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def get_db() -> Session:
    """
    Get database session.

    Usage:
        db = next(get_db())
        # or in FastAPI endpoints:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session.

    Usage:
        with get_db_context() as db:
            # use db
            pass
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_db():
    """Reset database (drop all tables and recreate). Use with caution!"""
    logger.warning("Resetting database - all data will be lost!")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Database reset complete")
