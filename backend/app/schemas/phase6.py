from datetime import datetime
from typing import Literal
import uuid

from pydantic import EmailStr, Field

from app.schemas.auth import StrictModel, UserResponse


class AnnouncementCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=6000)
    department_id: int | None = Field(default=None, ge=1)


class AnnouncementUpdateRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, min_length=1, max_length=6000)
    archived: bool | None = None


class AnnouncementResponse(StrictModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    department_id: int
    title: str
    body: str
    created_by: uuid.UUID
    updated_by: uuid.UUID
    archived_at: datetime | None
    revision: int
    created_at: datetime
    updated_at: datetime


class DashboardTaskItem(StrictModel):
    id: uuid.UUID
    title: str
    status: str
    priority: str
    kind: str
    due_date: str | None


class DashboardDocumentItem(StrictModel):
    id: uuid.UUID
    title: str
    category: str
    updated_at: datetime


class DashboardDepartmentSummary(StrictModel):
    active_employee_count: int
    open_assigned_task_count: int
    overdue_assigned_task_count: int


class StaffDashboardResponse(StrictModel):
    user: UserResponse
    stats: dict[str, int]
    priority_tasks: list[DashboardTaskItem]
    announcements: list[AnnouncementResponse]
    recent_documents: list[DashboardDocumentItem]
    department_summary: DashboardDepartmentSummary | None = None


class AuditLogResponse(StrictModel):
    id: int
    actor_id: uuid.UUID | None
    actor_name: str | None = None
    action: str
    entity_type: str | None
    entity_id: str | None
    result: str
    request_id: str
    details: dict
    created_at: datetime


class AdminOverviewResponse(StrictModel):
    stats: dict[str, int]
    latest_audit_events: list[AuditLogResponse]
    readiness: dict[str, bool]


class AdminUserCreateRequest(StrictModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    employee_code: str = Field(min_length=1, max_length=30)
    job_title: str | None = Field(default=None, max_length=120)
    department_role: Literal["EMPLOYEE", "MANAGER"] = "EMPLOYEE"
    department_id: int | None = Field(default=None, ge=1)


class AdminUserUpdateRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    employee_code: str | None = Field(default=None, min_length=1, max_length=30)
    job_title: str | None = Field(default=None, max_length=120)
    department_role: Literal["EMPLOYEE", "MANAGER"] | None = None
    is_active: bool | None = None


class AdminUserResponse(UserResponse):
    pass


class AdminUserCreateResponse(StrictModel):
    user: AdminUserResponse
    temporary_password: str


class AdminUserListResponse(StrictModel):
    items: list[AdminUserResponse]
    page: int
    page_size: int
    total: int


class PasswordResetRequest(StrictModel):
    admin_password: str = Field(min_length=1, max_length=256)


class PasswordResetResponse(StrictModel):
    user: AdminUserResponse
    temporary_password: str


class AuditLogListResponse(StrictModel):
    items: list[AuditLogResponse]
    page: int
    page_size: int
    total: int
 
