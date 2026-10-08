"""Simplify documents around company and department knowledge.

Revision ID: 0002_simplify_document_scope
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_simplify_document_scope"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("knowledge_scope", sa.String(length=20), server_default="DEPARTMENT", nullable=False),
    )
    op.alter_column("documents", "department_id", existing_type=sa.SmallInteger(), nullable=True)

    op.drop_index("ix_documents_department_visibility_status", table_name="documents")
    op.drop_constraint("ck_documents_visibility", "documents", type_="check")
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.drop_column("documents", "tags")
    op.drop_column("documents", "visibility")
    op.drop_column("documents", "status")
    op.drop_column("documents", "effective_from")

    op.create_check_constraint(
        "ck_documents_knowledge_scope",
        "documents",
        "(knowledge_scope = 'COMPANY' AND department_id IS NULL) OR "
        "(knowledge_scope = 'DEPARTMENT' AND department_id IS NOT NULL)",
    )
    op.create_index("ix_documents_scope_department", "documents", ["knowledge_scope", "department_id"])
    op.alter_column("documents", "knowledge_scope", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_documents_scope_department", table_name="documents")
    op.drop_constraint("ck_documents_knowledge_scope", "documents", type_="check")

    op.add_column("documents", sa.Column("effective_from", sa.Date(), nullable=True))
    op.add_column("documents", sa.Column("status", sa.String(length=20), server_default="PUBLISHED", nullable=False))
    op.add_column("documents", sa.Column("visibility", sa.String(length=20), server_default="DEPARTMENT", nullable=False))
    op.add_column("documents", sa.Column("tags", sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False))
    op.create_check_constraint("ck_documents_status", "documents", "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')")
    op.create_check_constraint("ck_documents_visibility", "documents", "visibility IN ('DEPARTMENT', 'MANAGER_ONLY')")
    op.create_index("ix_documents_department_visibility_status", "documents", ["department_id", "visibility", "status"])

    op.execute("UPDATE documents SET department_id = 1 WHERE department_id IS NULL")
    op.alter_column("documents", "department_id", existing_type=sa.SmallInteger(), nullable=False)
    op.drop_column("documents", "knowledge_scope")
