from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.routes.documents import _document_scope
from app.core.auth import Principal, require_admin, require_staff
from app.core.config import get_settings
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.document_bookmark import DocumentBookmark
from app.models.task import Task
from app.models.user import User
from app.schemas.phase6 import (
    AdminOverviewResponse,
    AnnouncementResponse,
    AuditLogResponse,
    DashboardDepartmentSummary,
    DashboardDocumentItem,
    DashboardTaskItem,
    StaffDashboardResponse,
)

router = APIRouter(tags=["dashboard"])


def _open_tasks(principal: Principal):
    return and_(
        Task.department_id == principal.user.department_id,
        Task.deleted_at.is_(None),
        Task.status.in_(["TODO", "IN_PROGRESS"]),
        or_((Task.kind == "PERSONAL") & (Task.created_by == principal.user.id), (Task.kind == "ASSIGNED") & (Task.assignee_id == principal.user.id)),
    )


def _dashboard_task(task: Task) -> DashboardTaskItem:
    return DashboardTaskItem(
        id=task.id,
        title=task.title,
        status=task.status,
        priority=task.priority,
        kind=task.kind,
        due_date=task.due_date.isoformat() if task.due_date else None,
    )


@router.get("/dashboard", response_model=StaffDashboardResponse)
def staff_dashboard(
    principal: Annotated[Principal, Depends(require_staff)],
    db: Annotated[Session, Depends(get_db)],
) -> StaffDashboardResponse:
    user = principal.user
    today = date.today()
    open_condition = _open_tasks(principal)
    overdue_condition = and_(open_condition, Task.due_date.is_not(None), Task.due_date < today)
    assigned_open_condition = and_(
        Task.department_id == user.department_id,
        Task.deleted_at.is_(None),
        Task.kind == "ASSIGNED",
        Task.assignee_id == user.id,
        Task.status.in_(["TODO", "IN_PROGRESS"]),
    )
    saved_condition = [DocumentBookmark.user_id == user.id, *_document_scope(principal)]
    stats = {
        "open_tasks": db.scalar(select(func.count()).select_from(Task).where(open_condition)) or 0,
        "overdue_tasks": db.scalar(select(func.count()).select_from(Task).where(overdue_condition)) or 0,
        "open_assigned_tasks": db.scalar(select(func.count()).select_from(Task).where(assigned_open_condition)) or 0,
        "saved_documents": db.scalar(select(func.count()).select_from(DocumentBookmark).join(Document, Document.id == DocumentBookmark.document_id).where(*saved_condition)) or 0,
    }
    tasks = db.scalars(
        select(Task).where(open_condition).order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.priority.desc(), Task.updated_at.desc()).limit(5)
    ).all()
    announcements = db.scalars(
        select(Announcement)
        .where(Announcement.department_id == user.department_id, Announcement.archived_at.is_(None))
        .order_by(Announcement.created_at.desc())
        .limit(3)
    ).all()
    documents = db.scalars(
        select(Document).where(*_document_scope(principal)).order_by(Document.updated_at.desc()).limit(5)
    ).all()
    summary = None
    if user.department_role == "MANAGER":
        summary = DashboardDepartmentSummary(
            active_employee_count=db.scalar(select(func.count()).select_from(User).where(User.account_type == "STAFF", User.department_id == user.department_id, User.department_role == "EMPLOYEE", User.is_active.is_(True))) or 0,
            open_assigned_task_count=db.scalar(select(func.count()).select_from(Task).where(Task.department_id == user.department_id, Task.kind == "ASSIGNED", Task.deleted_at.is_(None), Task.status.in_(["TODO", "IN_PROGRESS"]))) or 0,
            overdue_assigned_task_count=db.scalar(select(func.count()).select_from(Task).where(Task.department_id == user.department_id, Task.kind == "ASSIGNED", Task.deleted_at.is_(None), Task.status.in_(["TODO", "IN_PROGRESS"]), Task.due_date.is_not(None), Task.due_date < today)) or 0,
        )
    return StaffDashboardResponse(
        user=user,
        stats=stats,
        priority_tasks=[_dashboard_task(item) for item in tasks],
        announcements=[AnnouncementResponse.model_validate(item) for item in announcements],
        recent_documents=[DashboardDocumentItem(id=item.id, title=item.title, category=item.category, updated_at=item.updated_at) for item in documents],
        department_summary=summary,
    )


def _audit_response(item: AuditLog, actor_name: str | None) -> AuditLogResponse:
    return AuditLogResponse(
        id=item.id,
        actor_id=item.actor_id,
        actor_name=actor_name,
        action=item.action,
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        result=item.result,
        request_id=item.request_id,
        details=item.details or {},
        created_at=item.created_at,
    )


@router.get("/admin/overview", response_model=AdminOverviewResponse)
def admin_overview(
    principal: Annotated[Principal, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminOverviewResponse:
    del principal
    staff = User.account_type == "STAFF"
    stats = {
        "active_staff_count": db.scalar(select(func.count()).select_from(User).where(staff, User.is_active.is_(True))) or 0,
        "employee_count": db.scalar(select(func.count()).select_from(User).where(staff, User.department_role == "EMPLOYEE")) or 0,
        "manager_count": db.scalar(select(func.count()).select_from(User).where(staff, User.department_role == "MANAGER")) or 0,
        "locked_account_count": db.scalar(select(func.count()).select_from(User).where(staff, User.is_active.is_(False))) or 0,
        "total_document_file_count": db.scalar(select(func.count()).select_from(Document)) or 0,
        "total_stored_file_bytes": db.scalar(select(func.coalesce(func.sum(Document.size_bytes), 0)).select_from(Document)) or 0,
    }
    audit_rows = db.execute(
        select(AuditLog, User.full_name).outerjoin(User, User.id == AuditLog.actor_id).order_by(AuditLog.created_at.desc()).limit(5)
    ).all()
    settings = get_settings()
    storage_path = settings.upload_dir
    readiness = {"api": True, "database": True, "storage": storage_path.exists() and storage_path.is_dir()}
    return AdminOverviewResponse(
        stats=stats,
        latest_audit_events=[_audit_response(item, actor_name) for item, actor_name in audit_rows],
        readiness=readiness,
    )
