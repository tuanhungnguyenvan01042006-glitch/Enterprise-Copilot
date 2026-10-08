from datetime import date, datetime, timezone
from typing import Annotated
import uuid
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.auth import Principal, require_manager, validate_csrf
from app.core.config import get_settings
from app.core.errors import api_error
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.task import Task
from app.models.user import User
from app.schemas.workspace import (
    DepartmentMemberListResponse,
    DepartmentMemberResponse,
    DepartmentTaskCreateRequest,
    DepartmentTaskListResponse,
    DepartmentTaskResponse,
    DepartmentTaskUpdateRequest,
    TaskPriority,
    TaskStatus,
)

router = APIRouter(prefix="/department", tags=["department"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now(ZoneInfo(get_settings().business_timezone)).date()


def _audit(db: Session, request: Request, principal: Principal, action: str, task: Task, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_id=principal.user.id,
        action=action,
        entity_type="task",
        entity_id=str(task.id),
        result="SUCCESS",
        request_id=getattr(request.state, "request_id", "unknown"),
        details=details or {},
    ))


def _manager(principal: Principal) -> None:
    user = principal.user
    if user.must_change_password:
        raise api_error(status.HTTP_403_FORBIDDEN, "PASSWORD_CHANGE_REQUIRED", "Bạn cần đổi mật khẩu trước khi tiếp tục.")
    if user.account_type != "STAFF" or user.department_role != "MANAGER" or user.department_id is None:
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Chức năng này chỉ dành cho quản lý.")


def _member(user: User) -> DepartmentMemberResponse:
    return DepartmentMemberResponse.model_validate(user)


def _task(task: Task, assignee: User, creator: User) -> DepartmentTaskResponse:
    return DepartmentTaskResponse(
        **{field: getattr(task, field) for field in (
            "id", "department_id", "kind", "title", "description", "status", "priority",
            "assignee_id", "created_by", "due_date", "completed_at", "revision", "created_at", "updated_at",
        )},
        assignee=_member(assignee),
        creator=_member(creator),
    )


def _task_filters(principal: Principal):
    return (
        Task.department_id == principal.user.department_id,
        Task.kind == "ASSIGNED",
        Task.deleted_at.is_(None),
    )


def _task_query(principal: Principal, assignee_id: uuid.UUID | None, task_status: str | None, priority: str | None, overdue: bool | None):
    conditions = list(_task_filters(principal))
    if assignee_id:
        conditions.append(Task.assignee_id == assignee_id)
    if task_status:
        conditions.append(Task.status == task_status)
    if priority:
        conditions.append(Task.priority == priority)
    if overdue is True:
        conditions.extend((Task.due_date < _today(), Task.status.in_(["TODO", "IN_PROGRESS"])))
    elif overdue is False:
        conditions.append(~((Task.due_date < _today()) & Task.status.in_(["TODO", "IN_PROGRESS"])))
    return conditions


def _joined_task_query(principal: Principal, conditions):
    assignee = aliased(User)
    creator = aliased(User)
    query = (
        select(Task, assignee, creator)
        .join(assignee, Task.assignee_id == assignee.id)
        .join(creator, Task.created_by == creator.id)
        .where(*conditions)
        .order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.updated_at.desc())
    )
    return query, assignee, creator


def _get_department_task(db: Session, principal: Principal, task_id: uuid.UUID):
    query, _, _ = _joined_task_query(principal, [*_task_filters(principal), Task.id == task_id])
    row = db.execute(query).one_or_none()
    if row is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy công việc.")
    return row


def _active_employee(db: Session, principal: Principal, user_id: uuid.UUID) -> User:
    user = db.scalar(select(User).where(
        User.id == user_id,
        User.account_type == "STAFF",
        User.department_id == principal.user.department_id,
        User.department_role == "EMPLOYEE",
        User.is_active.is_(True),
    ))
    if user is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_ASSIGNEE", "Người nhận phải là nhân viên đang hoạt động trong phòng ban.")
    return user


@router.get("/members", response_model=DepartmentMemberListResponse)
def list_members(
    principal: Annotated[Principal, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DepartmentMemberListResponse:
    conditions = (User.account_type == "STAFF", User.department_id == principal.user.department_id)
    total = db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    users = db.scalars(select(User).where(*conditions).order_by(User.is_active.desc(), User.full_name.asc()).offset((page - 1) * page_size).limit(page_size)).all()
    return DepartmentMemberListResponse(items=[_member(user) for user in users], page=page, page_size=page_size, total=total)


@router.get("/tasks", response_model=DepartmentTaskListResponse)
def list_department_tasks(
    principal: Annotated[Principal, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db)],
    assignee_id: uuid.UUID | None = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    overdue: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DepartmentTaskListResponse:
    conditions = _task_query(principal, assignee_id, task_status, priority, overdue)
    total = db.scalar(select(func.count()).select_from(Task).where(*conditions)) or 0
    query, _, _ = _joined_task_query(principal, conditions)
    rows = db.execute(query.offset((page - 1) * page_size).limit(page_size)).all()
    return DepartmentTaskListResponse(items=[_task(task, assignee, creator) for task, assignee, creator in rows], page=page, page_size=page_size, total=total)


@router.get("/tasks/{task_id}", response_model=DepartmentTaskResponse)
def get_department_task(
    task_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_manager)],
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentTaskResponse:
    task, assignee, creator = _get_department_task(db, principal, task_id)
    return _task(task, assignee, creator)


@router.post("/tasks", response_model=DepartmentTaskResponse, status_code=status.HTTP_201_CREATED)
def create_department_task(
    payload: DepartmentTaskCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentTaskResponse:
    _manager(principal)
    assignee = _active_employee(db, principal, payload.assignee_id)
    title = payload.title.strip()
    if not title:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
    task = Task(
        department_id=principal.user.department_id,
        kind="ASSIGNED",
        title=title,
        description=payload.description,
        status="TODO",
        priority=payload.priority,
        due_date=payload.due_date,
        assignee_id=assignee.id,
        created_by=principal.user.id,
    )
    db.add(task)
    db.flush()
    _audit(db, request, principal, "TASK_ASSIGNED", task, {"assignee_id": str(assignee.id)})
    db.commit()
    task, assignee, creator = _get_department_task(db, principal, task.id)
    return _task(task, assignee, creator)


@router.patch("/tasks/{task_id}", response_model=DepartmentTaskResponse)
def update_department_task(
    task_id: uuid.UUID,
    payload: DepartmentTaskUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentTaskResponse:
    _manager(principal)
    task, _, _ = _get_department_task(db, principal, task_id)
    changes = payload.model_fields_set - {"expected_revision"}
    if not changes:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Cần có ít nhất một trường cần cập nhật.")
    if task.revision != payload.expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Dữ liệu đã được cập nhật. Vui lòng tải lại trước khi lưu.")
    if "title" in changes:
        title = (payload.title or "").strip()
        if not title:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
        task.title = title
    if "description" in changes:
        task.description = payload.description
    if "priority" in changes:
        task.priority = payload.priority
    if "due_date" in changes:
        task.due_date = payload.due_date
    if "assignee_id" in changes:
        if payload.assignee_id is None:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_ASSIGNEE", "Người nhận không được để trống.")
        assignee = _active_employee(db, principal, payload.assignee_id)
        task.assignee_id = assignee.id
    if "status" in changes:
        if payload.status is None:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_STATUS", "Trạng thái không được để trống.")
        task.status = payload.status
        task.completed_at = _now() if payload.status == "DONE" else None
    if "priority" in changes and payload.priority is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_PRIORITY", "Độ ưu tiên không được để trống.")
    task.revision += 1
    task.updated_at = _now()
    _audit(db, request, principal, "TASK_UPDATED", task, {"fields": sorted(changes)})
    db.commit()
    task, assignee, creator = _get_department_task(db, principal, task.id)
    return _task(task, assignee, creator)
