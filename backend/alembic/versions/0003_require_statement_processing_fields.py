"""Require statement processing fields.

Revision ID: 0003_require_statement_processing_fields
Revises: 0002_strengthen_financial_schema
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_require_statement_processing_fields"
down_revision: Union[str, None] = "0002_strengthen_financial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATEMENT_STATUS = sa.Enum(
    "UPLOADED", "PROCESSING", "PROCESSED", "FAILED", name="statementstatus"
)


def upgrade() -> None:
    op.execute("UPDATE statements SET status = 'UPLOADED' WHERE status IS NULL")
    op.execute("UPDATE statements SET uploaded_at = CURRENT_TIMESTAMP WHERE uploaded_at IS NULL")
    op.execute("UPDATE statements SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

    with op.batch_alter_table("statements", recreate="always") as batch_op:
        batch_op.alter_column("status", existing_type=_STATEMENT_STATUS, nullable=False)
        batch_op.alter_column(
            "uploaded_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        batch_op.alter_column(
            "updated_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("statements", recreate="always") as batch_op:
        batch_op.alter_column("status", existing_type=_STATEMENT_STATUS, nullable=True)
        batch_op.alter_column(
            "uploaded_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
        batch_op.alter_column(
            "updated_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
