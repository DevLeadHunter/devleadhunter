"""
Database configuration and session management.
"""

import logging

# Configure SQLAlchemy logging BEFORE importing SQLAlchemy
# This ensures logs are suppressed even if engine is created during import
# Set level to ERROR to completely suppress INFO logs
sqlalchemy_engine_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_engine_logger.setLevel(logging.ERROR)
sqlalchemy_engine_logger.propagate = False

sqlalchemy_pool_logger = logging.getLogger("sqlalchemy.pool")
sqlalchemy_pool_logger.setLevel(logging.ERROR)
sqlalchemy_pool_logger.propagate = False

sqlalchemy_dialects_logger = logging.getLogger("sqlalchemy.dialects")
sqlalchemy_dialects_logger.setLevel(logging.ERROR)
sqlalchemy_dialects_logger.propagate = False

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

# Create database engine
# echo=False to disable SQL query logging (we handle logging separately)
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=300, echo=False)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Options of the tables that hold visitor or business text (emoji, ligatures, Word bullets): utf8mb4 whatever the
# schema's default charset, which older databases kept in latin1.
UTF8MB4_TABLE_OPTIONS: dict[str, str] = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


# Create Base class for models
class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


def get_db():
    """
    Database dependency for FastAPI routes.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create the table of every model that has none yet; an existing table is never altered.

    The ``models`` package imports every model, which registers its table.
    """
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
