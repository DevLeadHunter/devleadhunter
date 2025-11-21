"""
User model for authentication and authorization.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.user_role import UserRole

if TYPE_CHECKING:
    from models.credit_transaction import CreditTransaction
    from models.support_ticket import SupportTicket
    from models.support_message import SupportMessage
    from models.email_account import EmailAccount
    from models.email_template import EmailTemplate
    from models.email_log import EmailLog
    from models.campaign import Campaign


class User(Base):
    """
    User model for authentication and authorization.
    
    Attributes:
        id: Unique identifier
        name: User's full name
        email: User's email address (unique)
        hashed_password: Hashed password
        role: User role (USER or ADMIN)
        is_active: Whether the user is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        credit_transactions: Relationship to credit transactions
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    
    # Relationship to credit transactions
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="SupportTicket.user_id"
    )
    assigned_support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket",
        back_populates="assigned_admin",
        foreign_keys="SupportTicket.assigned_admin_id"
    )
    support_messages: Mapped[list["SupportMessage"]] = relationship(
        "SupportMessage",
        back_populates="sender",
        cascade="all, delete-orphan",
        foreign_keys="SupportMessage.sender_id"
    )
    email_accounts: Mapped[list["EmailAccount"]] = relationship(
        "EmailAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    email_templates: Mapped[list["EmailTemplate"]] = relationship(
        "EmailTemplate",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    email_logs: Mapped[list["EmailLog"]] = relationship(
        "EmailLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User id={self.id} name={self.name} email={self.email} role={self.role}>"

