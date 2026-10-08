"""Restore document lifecycle status for Phase 6 dashboards."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_document_status"
down_revision: str | None = "0002_simplify_document_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing Phase 5 documents were readable by STAFF; preserve that behavior
    # while new documents created by the application start as DRAFT explicitly.
    op.add_column("documents", sa.Column("status", sa.String(length=20), server_default="PUBLISHED", nullable=False))
    op.create_check_constraint("ck_documents_status", "documents", "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')")


def downgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.drop_column("documents", "status")
