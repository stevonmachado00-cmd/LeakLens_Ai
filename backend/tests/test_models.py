from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.statement import (
    BillingCycle,
    Statement,
    StatementStatus,
    Subscription,
    SubscriptionStatus,
    Transaction,
)
from app.models.user import User


def test_user_requires_full_name(db_session):
    with db_session.begin_nested():
        db_session.add(
            User(email="missing-name@example.com", hashed_password="hash", full_name=None)
        )

        with pytest.raises(IntegrityError):
            db_session.flush()


def test_financial_amounts_are_stored_as_decimals(db_session):
    user = User(
        email="schema@example.com", full_name="Schema User", hashed_password="hash"
    )
    db_session.add(user)
    db_session.flush()

    statement = Statement(
        user_id=user.id,
        filename="statement.csv",
        original_filename="statement.csv",
        file_type="csv",
        file_size=100,
        status=StatementStatus.UPLOADED,
    )
    db_session.add(statement)
    db_session.flush()

    transaction = Transaction(
        statement_id=statement.id,
        date=datetime.now(timezone.utc),
        merchant="Example Merchant",
        description="Example charge",
        amount=Decimal("12.34"),
        currency="USD",
    )
    subscription = Subscription(
        user_id=user.id,
        merchant="Example Merchant",
        normalized_merchant="example merchant",
        billing_cycle=BillingCycle.MONTHLY,
        average_amount=Decimal("12.34"),
        last_charge_date=datetime.now(timezone.utc),
        confidence=Decimal("0.900"),
        status=SubscriptionStatus.DETECTED,
    )
    db_session.add_all([transaction, subscription])
    db_session.flush()
    db_session.expire_all()

    stored_transaction = db_session.get(Transaction, transaction.id)
    stored_subscription = db_session.get(Subscription, subscription.id)

    assert stored_transaction.amount == Decimal("12.34")
    assert stored_subscription.average_amount == Decimal("12.34")
