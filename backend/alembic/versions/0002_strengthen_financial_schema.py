"""Strengthen financial data integrity and analysis indexes.

Revision ID: 0002_strengthen_financial_schema
Revises: 0001_initial_schema
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_strengthen_financial_schema"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    with op.batch_alter_table("user", recreate="always") as batch_op:
        batch_op.alter_column("full_name", existing_type=sa.String(), nullable=False)
        batch_op.alter_column(
            "is_active",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )

    with op.batch_alter_table(
        "statements", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint("fk_statements_user_id_user", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_statements_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_statements_status",
            "status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'FAILED')",
        )
        batch_op.create_check_constraint(
            "ck_statements_file_type", "file_type IN ('pdf', 'csv')"
        )
        batch_op.create_check_constraint("ck_statements_file_size", "file_size >= 0")
        batch_op.create_index(
            "ix_statements_user_id_uploaded_at", ["user_id", "uploaded_at"], unique=False
        )

    with op.batch_alter_table(
        "transactions", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint("fk_transactions_statement_id_statements", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_transactions_statement_id_statements",
            "statements",
            ["statement_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "date", existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True), nullable=False
        )
        batch_op.alter_column(
            "amount", existing_type=sa.Float(), type_=sa.Numeric(12, 2), nullable=False
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.create_index(
            "ix_transactions_statement_id_date", ["statement_id", "date"], unique=False
        )
        batch_op.create_index("ix_transactions_merchant_date", ["merchant", "date"], unique=False)

    with op.batch_alter_table(
        "subscriptions", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint("fk_subscriptions_user_id_user", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_subscriptions_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "average_amount", existing_type=sa.Float(), type_=sa.Numeric(12, 2), nullable=False
        )
        batch_op.alter_column(
            "last_charge_date", existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True), nullable=False
        )
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.create_index(
            "ix_subscriptions_user_id_status", ["user_id", "status"], unique=False
        )
        batch_op.create_index(
            "ix_subscriptions_user_id_merchant", ["user_id", "merchant"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "subscriptions", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_index("ix_subscriptions_user_id_merchant")
        batch_op.drop_index("ix_subscriptions_user_id_status")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.alter_column(
            "last_charge_date", existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(), nullable=False
        )
        batch_op.alter_column(
            "average_amount", existing_type=sa.Numeric(12, 2), type_=sa.Float(), nullable=False
        )
        batch_op.drop_constraint("fk_subscriptions_user_id_user", type_="foreignkey")
        batch_op.create_foreign_key(None, "user", ["user_id"], ["id"])

    with op.batch_alter_table(
        "transactions", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_index("ix_transactions_merchant_date")
        batch_op.drop_index("ix_transactions_statement_id_date")
        batch_op.drop_column("created_at")
        batch_op.alter_column(
            "amount", existing_type=sa.Numeric(12, 2), type_=sa.Float(), nullable=False
        )
        batch_op.alter_column(
            "date", existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(), nullable=False
        )
        batch_op.drop_constraint("fk_transactions_statement_id_statements", type_="foreignkey")
        batch_op.create_foreign_key(None, "statements", ["statement_id"], ["id"])

    with op.batch_alter_table(
        "statements", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_index("ix_statements_user_id_uploaded_at")
        batch_op.drop_constraint("ck_statements_file_size", type_="check")
        batch_op.drop_constraint("ck_statements_file_type", type_="check")
        batch_op.drop_constraint("ck_statements_status", type_="check")
        batch_op.drop_column("updated_at")
        batch_op.drop_constraint("fk_statements_user_id_user", type_="foreignkey")
        batch_op.create_foreign_key(None, "user", ["user_id"], ["id"])

    with op.batch_alter_table("user", recreate="always") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.alter_column(
            "is_active", existing_type=sa.Boolean(), nullable=True, server_default=None
        )
        batch_op.alter_column("full_name", existing_type=sa.String(), nullable=True)
