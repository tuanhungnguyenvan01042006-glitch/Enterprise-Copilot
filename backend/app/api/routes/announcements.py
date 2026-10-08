from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_ready_principal, validate_ready_csrf
from app.core.errors import api_error
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.audit_log import AuditLog
from app.models.department import Department
from app.schemas.phase6 import AnnouncementCreateRequest, AnnouncementResponse, AnnouncementUpdateRequest

router = APIRouter(prefix="/announcements", tags=["announcements"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db: Session, request: Request, principal: Principal, action: str, announcement: Announcement, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_id=principal.user.id,
        action=action,
        entity_type="announcement",
        entity_id=str(announcement.id),
        result="SUCCESS",
        request_id=getattr(request.state, "request_id", "unknown"),
        details=details or {},
    ))


def _can_manage(principal: Principal, announcement: Announcement | None = None) -> bool:
    if principal.user.account_type == "ADMIN":
        return True
    return bool(
        principal.user.account_type == "STAFF"
        and principal.user.department_role == "MANAGER"
        and announcement is not None
        and announcement.department_id == principal.user.department_id
    )


def _department_id(db: Session, principal: Principal, requested: int | None) -> int:
    if principal.user.account_type == "STAFF":
        if principal.user.department_id is None:
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Tài khoản chưa thuộc phòng ban.")
        if requested is not None and requested != principal.user.department_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Không được tạo thông báo cho phòng ban khác.")
        return principal.user.department_id
    department_id = requested or db.scalar(select(Department.id).order_by(Department.id))
    if department_id is None or db.get(Department, department_id) is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_DEPARTMENT", "Phòng ban không tồn tại.")
    return department_id


@router.get("", response_model=list[AnnouncementResponse])
def list_announcements(
    principal: Annotated[Principal, Depends(require_ready_principal)],
    db: Annotated[Session, Depends(get_db)],
    include_archived: bool = Query(default=False),
) -> list[AnnouncementResponse]:
    user = principal.user
    query = select(Announcement)
    if user.account_type == "ADMIN":
        if not include_archived:
            query = query.where(Announcement.archived_at.is_(None))
    else:
        if user.department_id is None:
            return []
        query = query.where(Announcement.department_id == user.department_id)
        if user.department_role != "MANAGER" or not include_archived:
            query = query.where(Announcement.archived_at.is_(None))
    return [AnnouncementResponse.model_validate(item) for item in db.scalars(query.order_by(Announcement.created_at.desc())).all()]


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_ready_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> AnnouncementResponse:
    if principal.user.account_type != "ADMIN" and principal.user.department_role != "MANAGER":
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Chỉ quản lý hoặc quản trị viên được tạo thông báo.")
    title = payload.title.strip()
    body = payload.body.strip()
    if not title or not body:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề và nội dung không được để trống.")
    department_id = _department_id(db, principal, payload.department_id)
    announcement = Announcement(
        department_id=department_id,
        title=title,
        body=body,
        created_by=principal.user.id,
        updated_by=principal.user.id,
    )
    db.add(announcement)
    db.flush()
    _audit(db, request, principal, "ANNOUNCEMENT_CREATED", announcement, {"department_id": department_id})
    db.commit()
    db.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_ready_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> AnnouncementResponse:
    if principal.user.account_type != "ADMIN" and principal.user.department_role != "MANAGER":
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Chỉ quản lý hoặc quản trị viên được sửa thông báo.")
    announcement = db.scalar(select(Announcement).where(Announcement.id == announcement_id).with_for_update())
    if announcement is None or not _can_manage(principal, announcement):
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy thông báo.")
    if announcement.revision != payload.expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Thông báo đã được cập nhật. Vui lòng tải lại.")
    changes = payload.model_fields_set - {"expected_revision"}
    if not changes:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Cần có ít nhất một trường cần cập nhật.")
    if "title" in changes:
        title = (payload.title or "").strip()
        if not title:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
        announcement.title = title
    if "body" in changes:
        body = (payload.body or "").strip()
        if not body:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Nội dung không được để trống.")
        announcement.body = body
    action = "ANNOUNCEMENT_UPDATED"
    if "archived" in changes:
        announcement.archived_at = _now() if payload.archived else None
        action = "ANNOUNCEMENT_ARCHIVED" if payload.archived else "ANNOUNCEMENT_RESTORED"
    announcement.updated_by = principal.user.id
    announcement.updated_at = _now()
    announcement.revision += 1
    _audit(db, request, principal, action, announcement, {"fields": sorted(changes)})
    db.commit()
    db.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)
