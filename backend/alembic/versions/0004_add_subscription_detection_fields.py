"""Add subscription detection fields and lifecycle constraints.

Revision ID: 0004_add_subscription_detection_fields
Revises: 0003_require_statement_processing_fields
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_add_subscription_detection_fields"
down_revision: Union[str, None] = "0003_require_statement_processing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BILLING_CYCLE = sa.Enum("WEEKLY", "MONTHLY", "QUARTERLY", "YEARLY", name="billingcycle", create_constraint=True)
_SUBSCRIPTION_STATUS = sa.Enum(
    "DETECTED", "CONFIRMED", "IGNORED", "CANCELLED", name="subscriptionstatus", create_constraint=True
)


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("normalized_merchant", sa.String(), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("confidence", sa.Numeric(4, 3), server_default=sa.text("0.000"), nullable=False),
    )
    op.execute("UPDATE subscriptions SET normalized_merchant = lower(trim(merchant))")
    op.execute(
        """
        UPDATE subscriptions
        SET billing_cycle = CASE lower(billing_cycle)
            WHEN 'weekly' THEN 'WEEKLY'
            WHEN 'monthly' THEN 'MONTHLY'
            WHEN 'quarterly' THEN 'QUARTERLY'
            WHEN 'yearly' THEN 'YEARLY'
            ELSE 'MONTHLY'
        END
        """
    )
    op.execute(
        """
        UPDATE subscriptions
        SET status = CASE lower(status)
            WHEN 'confirmed' THEN 'CONFIRMED'
            WHEN 'ignored' THEN 'IGNORED'
            WHEN 'cancelled' THEN 'CANCELLED'
            ELSE 'DETECTED'
        END
        """
    )

    with op.batch_alter_table("subscriptions", recreate="always") as batch_op:
        batch_op.alter_column("normalized_merchant", existing_type=sa.String(), nullable=False)
        batch_op.alter_column("billing_cycle", existing_type=sa.String(), type_=_BILLING_CYCLE, nullable=False)
        batch_op.alter_column("status", existing_type=sa.String(), type_=_SUBSCRIPTION_STATUS, nullable=False)
        batch_op.create_index(
            "ix_subscriptions_user_id_normalized_merchant", ["user_id", "normalized_merchant"], unique=False
        )
        batch_op.create_unique_constraint(
            "uq_subscriptions_user_merchant_cycle",
            ["user_id", "normalized_merchant", "billing_cycle"],
        )


def downgrade() -> None:
    with op.batch_alter_table("subscriptions", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_subscriptions_user_merchant_cycle", type_="unique")
        batch_op.drop_index("ix_subscriptions_user_id_normalized_merchant")
        batch_op.alter_column("status", existing_type=_SUBSCRIPTION_STATUS, type_=sa.String(), nullable=False)
        batch_op.alter_column("billing_cycle", existing_type=_BILLING_CYCLE, type_=sa.String(), nullable=False)
        batch_op.drop_column("confidence")
        batch_op.drop_column("normalized_merchant")
