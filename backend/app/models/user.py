import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(account_type = 'STAFF' AND department_id IS NOT NULL AND department_role IS NOT NULL AND employee_code IS NOT NULL) OR "
            "(account_type = 'ADMIN' AND department_id IS NULL AND department_role IS NULL AND employee_code IS NULL)",
            name="ck_users_account_scope",
        ),
        CheckConstraint("account_type IN ('STAFF', 'ADMIN')", name="ck_users_account_type"),
        CheckConstraint("department_role IS NULL OR department_role IN ('EMPLOYEE', 'MANAGER')", name="ck_users_department_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    employee_code: Mapped[str | None] = mapped_column(String(30), unique=True)
    job_title: Mapped[str | None] = mapped_column(String(120))
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    department_role: Mapped[str | None] = mapped_column(String(20))
    department_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
  