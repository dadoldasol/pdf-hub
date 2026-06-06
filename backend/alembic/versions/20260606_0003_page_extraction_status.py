"""Add page extraction status fields.

Revision ID: 20260606_0003
Revises: 20260603_0002
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260606_0003"
down_revision: Union[str, None] = "20260603_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_pages",
        sa.Column(
            "extraction_status",
            sa.String(length=32),
            nullable=False,
            server_default="completed",
        ),
    )
    op.add_column("document_pages", sa.Column("extraction_error", sa.Text(), nullable=True))
    op.add_column("document_pages", sa.Column("extraction_seconds", sa.Float(), nullable=True))
    op.alter_column("document_pages", "extraction_status", server_default=None)


def downgrade() -> None:
    op.drop_column("document_pages", "extraction_seconds")
    op.drop_column("document_pages", "extraction_error")
    op.drop_column("document_pages", "extraction_status")
