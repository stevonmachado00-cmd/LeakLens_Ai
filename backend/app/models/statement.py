from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database.session import Base

class StatementStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class BillingCycle(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(str, enum.Enum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    IGNORED = "ignored"
    CANCELLED = "cancelled"

class Statement(Base):
    __tablename__ = "statements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED')",
            name="ck_statements_status",
        ),
        CheckConstraint("file_type IN ('pdf', 'csv')", name="ck_statements_file_type"),
        CheckConstraint("file_size >= 0", name="ck_statements_file_size"),
        Index("ix_statements_user_id_uploaded_at", "user_id", "uploaded_at"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf or csv
    file_size = Column(Integer, nullable=False)
    status = Column(Enum(StatementStatus), default=StatementStatus.UPLOADED, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_statement_id_date", "statement_id", "date"),
        Index("ix_transactions_merchant_date", "merchant", "date"),
    )

    id = Column(Integer, primary_key=True)
    statement_id = Column(Integer, ForeignKey("statements.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    merchant = Column(String, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    statement = relationship("Statement", back_populates="transactions")

class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_id_status", "user_id", "status"),
        Index("ix_subscriptions_user_id_merchant", "user_id", "merchant"),
        UniqueConstraint(
            "user_id", "normalized_merchant", "billing_cycle", name="uq_subscriptions_user_merchant_cycle"
        ),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    merchant = Column(String, nullable=False)
    normalized_merchant = Column(String, nullable=False)
    billing_cycle = Column(Enum(BillingCycle, create_constraint=True), nullable=False)
    average_amount = Column(Numeric(12, 2), nullable=False)
    last_charge_date = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False)
    status = Column(Enum(SubscriptionStatus, create_constraint=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="subscriptions")
