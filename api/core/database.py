"""
Database configuration and session management.
"""
import logging

# Configure SQLAlchemy logging BEFORE importing SQLAlchemy
# This ensures logs are suppressed even if engine is created during import
# Set level to ERROR to completely suppress INFO logs
sqlalchemy_engine_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_engine_logger.setLevel(logging.ERROR)
sqlalchemy_engine_logger.propagate = False

sqlalchemy_pool_logger = logging.getLogger('sqlalchemy.pool')
sqlalchemy_pool_logger.setLevel(logging.ERROR)
sqlalchemy_pool_logger.propagate = False

sqlalchemy_dialects_logger = logging.getLogger('sqlalchemy.dialects')
sqlalchemy_dialects_logger.setLevel(logging.ERROR)
sqlalchemy_dialects_logger.propagate = False

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings


# Create database engine
# echo=False to disable SQL query logging (we handle logging separately)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    Initialize database tables.
    
    This function creates all tables defined in the models.
    """
    from models.user import User  # noqa: F401
    from models.credit_settings import CreditSettings  # noqa: F401
    from models.credit_transaction import CreditTransaction  # noqa: F401
    from models.support_ticket import SupportTicket  # noqa: F401
    from models.support_message import SupportMessage  # noqa: F401
    from models.support_attachment import SupportAttachment  # noqa: F401
    from models.email_account import EmailAccount  # noqa: F401
    from models.email_template import EmailTemplate  # noqa: F401
    from models.email_log import EmailLog  # noqa: F401
    from models.prospect_db import ProspectDB  # noqa: F401
    from models.campaign import Campaign  # noqa: F401
    from models.email_unsubscribe import EmailUnsubscribe  # noqa: F401
    from models.prospect_interaction import ProspectInteraction  # noqa: F401
    from models.demo_site import DemoSite  # noqa: F401
    from models.prospect_enrichment import ProspectEnrichment  # noqa: F401
    from models.order import Order  # noqa: F401
    from models.campaign_follow_up import CampaignFollowUp  # noqa: F401
    from models.email_queue import EmailQueue  # noqa: F401
    from models.resend_config import ResendConfig  # noqa: F401
    from models.acquisition_run import AcquisitionRun  # noqa: F401
    from models.acquisition_run_item import AcquisitionRunItem  # noqa: F401

    Base.metadata.create_all(bind=engine)

