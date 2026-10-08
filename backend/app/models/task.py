import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("kind IN ('PERSONAL', 'ASSIGNED')", name="ck_tasks_kind"),
        CheckConstraint("status IN ('TODO', 'IN_PROGRESS', 'DONE', 'CANCELLED')", name="ck_tasks_status"),
        CheckConstraint("priority IN ('LOW', 'NORMAL', 'HIGH')", name="ck_tasks_priority"),
        CheckConstraint("status = 'DONE' AND completed_at IS NOT NULL OR status <> 'DONE' AND completed_at IS NULL", name="ck_tasks_completed_at"),
        CheckConstraint("kind <> 'PERSONAL' OR created_by = assignee_id", name="ck_tasks_personal_owner"),
        Index("ix_tasks_assignee_kind_status", "assignee_id", "kind", "status"),
        Index("ix_tasks_department_kind_status", "department_id", "kind", "status"),
        Index("ix_tasks_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("departments.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="TODO", server_default="TODO")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL", server_default="NORMAL")
    assignee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

 