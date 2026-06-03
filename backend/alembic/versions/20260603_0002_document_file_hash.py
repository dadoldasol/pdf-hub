"""Add document file hash for duplicate detection.

Revision ID: 20260603_0002
Revises: 20260531_0001
Create Date: 2026-06-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260603_0002"
down_revision: Union[str, None] = "20260531_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("file_hash", sa.String(length=64), nullable=True))
    op.create_index(
        "uq_documents_file_hash",
        "documents",
        ["file_hash"],
        unique=True,
        postgresql_where=sa.text("file_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_documents_file_hash", table_name="documents")
    op.drop_column("documents", "file_hash")
