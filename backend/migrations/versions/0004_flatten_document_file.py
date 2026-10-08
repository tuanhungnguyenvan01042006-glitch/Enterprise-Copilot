"""Flatten the current document file into the documents table.

The latest document version is copied into the new file columns before the
document_versions table is removed. Historical versions are intentionally not
retained by the simplified document model.
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_flatten_document_file"
down_revision: str | None = "0003_add_document_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("original_filename", sa.String(length=255), nullable=True))
    op.add_column("documents", sa.Column("storage_key", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("checksum_sha256", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_documents_uploaded_by_users", "documents", "users", ["uploaded_by"], ["id"])

    op.execute(
        sa.text(
            """
            WITH ranked_versions AS (
                SELECT
                    dv.document_id,
                    dv.original_filename,
                    dv.storage_key,
                    dv.mime_type,
                    dv.size_bytes,
                    dv.checksum_sha256,
                    dv.uploaded_by,
                    dv.created_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY dv.document_id
                        ORDER BY dv.version_number DESC
                    ) AS row_number
                FROM document_versions AS dv
            )
            UPDATE documents AS d
            SET
                original_filename = v.original_filename,
                storage_key = v.storage_key,
                mime_type = v.mime_type,
                size_bytes = v.size_bytes,
                checksum_sha256 = v.checksum_sha256,
                uploaded_by = v.uploaded_by,
                uploaded_at = v.created_at
            FROM ranked_versions AS v
            WHERE v.document_id = d.id AND v.row_number = 1
            """
        )
    )

    connection = op.get_bind()
    missing_files = connection.scalar(sa.text("SELECT count(*) FROM documents WHERE storage_key IS NULL")) or 0
    if missing_files:
        raise RuntimeError(f"Cannot flatten {missing_files} documents without a document version.")

    for column in ("original_filename", "storage_key", "mime_type", "size_bytes", "checksum_sha256", "uploaded_by", "uploaded_at"):
        op.alter_column("documents", column, nullable=False)
    op.create_unique_constraint("uq_documents_storage_key", "documents", ["storage_key"])

    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.drop_column("documents", "status")
    op.drop_table("document_versions")


def downgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("version_number > 0", name="ck_document_versions_positive_number"),
        sa.CheckConstraint("size_bytes > 0", name="ck_document_versions_positive_size"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_versions_document_number"),
    )

    connection = op.get_bind()
    version_table = sa.table(
        "document_versions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("document_id", postgresql.UUID(as_uuid=True)),
        sa.column("version_number", sa.Integer()),
        sa.column("original_filename", sa.String()),
        sa.column("storage_key", sa.Text()),
        sa.column("mime_type", sa.String()),
        sa.column("size_bytes", sa.BigInteger()),
        sa.column("checksum_sha256", sa.String()),
        sa.column("uploaded_by", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    documents = connection.execute(
        sa.text(
            """
            SELECT id, original_filename, storage_key, mime_type, size_bytes,
                   checksum_sha256, uploaded_by, uploaded_at
            FROM documents
            """
        )
    ).mappings()
    op.bulk_insert(
        version_table,
        [
            {
                "id": uuid.uuid4(),
                "document_id": row["id"],
                "version_number": 1,
                "original_filename": row["original_filename"],
                "storage_key": row["storage_key"],
                "mime_type": row["mime_type"],
                "size_bytes": row["size_bytes"],
                "checksum_sha256": row["checksum_sha256"],
                "uploaded_by": row["uploaded_by"],
                "created_at": row["uploaded_at"],
            }
            for row in documents
        ],
    )

    op.drop_constraint("uq_documents_storage_key", "documents", type_="unique")
    op.drop_constraint("fk_documents_uploaded_by_users", "documents", type_="foreignkey")
    for column in ("uploaded_at", "uploaded_by", "checksum_sha256", "size_bytes", "mime_type", "storage_key", "original_filename"):
        op.drop_column("documents", column)
    op.add_column("documents", sa.Column("status", sa.String(length=20), server_default="PUBLISHED", nullable=False))
    op.create_check_constraint("ck_documents_status", "documents", "status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')")
