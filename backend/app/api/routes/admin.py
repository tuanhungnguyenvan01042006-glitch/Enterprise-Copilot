from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_admin, revoke_user_sessions, validate_ready_csrf
from app.core.errors import api_error
from app.core.security import generate_token, hash_password, verify_password
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.user import User
from app.schemas.phase6 import (
    AdminUserCreateRequest,
    AdminUserCreateResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    AuditLogListResponse,
    AuditLogResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db: Session, request: Request, principal: Principal, action: str, entity_type: str, entity_id: object, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_id=principal.user.id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        result="SUCCESS",
        request_id=getattr(request.state, "request_id", "unknown"),
        details=details or {},
    ))


def _get_staff(db: Session, user_id: uuid.UUID, *, lock: bool = False) -> User:
    query = select(User).where(User.id == user_id, User.account_type == "STAFF")        # tìm kiếm staff theo user.id 
    if lock:
        query = query.with_for_update()   # Lock là tham số được truyền vào(mặc định là false), nếu là true nó sẽ gắn cụm with for update vào câu querry
    user = db.scalar(query)
    if user is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy tài khoản STAFF.")
    return user
"""
giải thích phần with for upadate : 
Cụ thể nó là cấu trúc querry .... For Update : Có tác dụng đối với 1 Transaction, mang ý nghĩa là khóa Đối tượng đó, cho tới khi kết thúc Transaction 
ta hiểu, với 1 chức năng API, nó sẽ sử dụng hàng loạt câu querry trong cùng 1 transaction 
* NOTE : cụm with_for_update sẽ luôn đi cùng select, nó sẽ khóa đối tượng selected,
ko cho transaction khác tác động tới Đối tượng selected. Tuy nhiên, các querry cùng transaction (phía dưới Querry Select with update) thì hoàn toàn vẫn có thể tác động được vào đối tượng selected 
---> Điều này có nghĩa : Vai trò của with_for_update là : để cho việc update 1 đối tượng nào đó an toàn hơn,
tránh trường hợp mâu thuẫn khi cùng 1 lúc 2 transaction muốn tác động đối tượng 

---> như vậy, mỗi khi thấy lock, with update, ta hiểu ngay dưới câu lệnh select này sẽ
là việc update đối tượng selected, và việc lock là để cho việc update an toàn  
"""

def _user_response(user: User) -> AdminUserResponse:
    return AdminUserResponse.model_validate(user)    # hàm chuyển từ User sang UserResponse(schema)


def _assert_unique(db: Session, email: str, employee_code: str, exclude_id: uuid.UUID | None = None) -> None:
    query = select(User).where(or_(User.email == email, User.employee_code == employee_code))
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    existing = db.scalar(query)
    if existing is not None:
        if existing.email == email:
            raise api_error(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "Email đã được sử dụng.")
        raise api_error(status.HTTP_409_CONFLICT, "EMPLOYEE_CODE_ALREADY_EXISTS", "Mã nhân viên đã được sử dụng.")

# Admin sẽ có quyền (chức năng) hạ cấp Manager của 1 phòng ban/ hoặc Inactive tài khoản Manager 
# Tuy nhiên lại có quy tắc, mỗi phòng ban, phải có ít nhất 1 Manager active, vậy nên hàm này nhằm bảo vệ Manager duy nhất (nếu xảy ra) tại phòng ban đó, ko bị xóa
def _protect_last_active_manager(db: Session, target: User, next_role: str, next_active: bool) -> None:
    is_demoting = target.is_active and target.department_role == "MANAGER" and (next_role != "MANAGER" or not next_active)
    # Đây là đang kiểm tra Target
    if not is_demoting:  
        return
    managers = db.scalars(
        select(User).where(
            User.account_type == "STAFF",
            User.department_id == target.department_id,
            User.department_role == "MANAGER",
            User.is_active.is_(True),
        ).with_for_update()
    ).all()
    if len(managers) <= 1:
        raise api_error(status.HTTP_409_CONFLICT, "LAST_ACTIVE_MANAGER", "Không thể khóa hoặc hạ vai trò Manager đang hoạt động cuối cùng.")


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    principal: Annotated[Principal, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, max_length=160),  # q là chuỗi tìm kiếm 
    role: str | None = Query(default=None),   # role : lọc theo vai trò 
    is_active: bool | None = Query(default=None),      
    page: int = Query(default=1, ge=1),   # số trang, mặc định là 1 (tức là mặc định, khi tìm kiếm users, thì mặc định sẽ là danh sách user ở trang 1), ko được nhỏ hơn 1
    page_size: int = Query(default=20, ge=1, le=100), # số user mỗi trang, mặc định là 20, giới hạn là từ 1 đến 100
) -> AdminUserListResponse:
    del principal
    query = select(User).where(User.account_type == "STAFF")
    if role:
        if role not in {"EMPLOYEE", "MANAGER"}:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_ROLE", "Vai trò không hợp lệ.")
        query = query.where(User.department_role == role)
    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))
    if q and q.strip():
        term = f"%{q.strip()}%"    # strip là để bỏ space ở 2 bên, còn % là để quy định q này có thể nằm ở bất kì vị trí nào trong string. --> làm cho việc tìm kiếm thuận tiện hơn nhiều, do người dùng ko cần nhập chính xác toàn bộ string giống trong Database
        query = query.where(or_(User.full_name.ilike(term), User.email.ilike(term), User.employee_code.ilike(term)))
    # Ở đây vốn là 1 thanh tìm kiếm, khi nhập q vào, nó sẽ đi đối chiếu với cả Full Name, Email, employee code --> Rất phù hợp với thực tiễn 
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0 
    # đếm số lượng user phù hợp với querry (chưa hiểu subquerry ở đây là gì)
    users = db.scalars(query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    # lấy đúng số lượng user thuộc trang mà phần querry page muốn lấy 
    return AdminUserListResponse(items=[_user_response(user) for user in users], page=page, page_size=page_size, total=total)

 
@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(user_id: uuid.UUID, principal: Annotated[Principal, Depends(require_admin)], db: Annotated[Session, Depends(get_db)]) -> AdminUserResponse:
    del principal
    return _user_response(_get_staff(db, user_id))


@router.post("/users", response_model=AdminUserCreateResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_ready_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserCreateResponse:
    email = str(payload.email).strip().lower()
    employee_code = payload.employee_code.strip()
    full_name = payload.full_name.strip()
    if not full_name or not employee_code:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Họ tên và mã nhân viên không được để trống.")
    _assert_unique(db, email, employee_code)
    department_id = payload.department_id or db.scalar(select(User.department_id).where(User.account_type == "STAFF", User.department_id.is_not(None)).limit(1))
    if department_id is None:
        department_id = 1
    if db.get(Department, department_id) is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_DEPARTMENT", "Phòng ban không tồn tại.")
    temporary_password = generate_token()
    user = User(
        email=email,
        password_hash=hash_password(temporary_password),
        full_name=full_name,
        employee_code=employee_code,
        job_title=payload.job_title.strip() if payload.job_title else None,
        account_type="STAFF",
        department_role=payload.department_role,
        department_id=department_id,
        is_active=True,
        must_change_password=True,
    )
    db.add(user)
    db.flush()
    _audit(db, request, principal, "USER_CREATED", "user", user.id, {"department_role": user.department_role})
    db.commit()
    db.refresh(user)
    return AdminUserCreateResponse(user=_user_response(user), temporary_password=temporary_password)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_ready_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserResponse:
    user = _get_staff(db, user_id, lock=True)
    if user.id == principal.user.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "SELF_ACCOUNT_PROTECTED", "Không thể quản lý chính tài khoản Admin hiện tại.")
    if user.revision != payload.expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Tài khoản đã được cập nhật. Vui lòng tải lại.")
    changes = payload.model_fields_set - {"expected_revision"}
    if not changes:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Cần có ít nhất một trường cần cập nhật.")
    next_role = payload.department_role if "department_role" in changes else user.department_role
    next_active = payload.is_active if "is_active" in changes else user.is_active
    _protect_last_active_manager(db, user, next_role or "EMPLOYEE", bool(next_active))
    if "full_name" in changes:
        full_name = (payload.full_name or "").strip()
        if not full_name:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Họ tên không được để trống.")
        user.full_name = full_name
    if "employee_code" in changes:
        employee_code = (payload.employee_code or "").strip()
        if not employee_code:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Mã nhân viên không được để trống.")
        _assert_unique(db, user.email, employee_code, user.id)
        user.employee_code = employee_code
    if "job_title" in changes:
        user.job_title = payload.job_title.strip() if payload.job_title else None
    if "department_role" in changes:
        user.department_role = payload.department_role
    if "is_active" in changes:
        user.is_active = payload.is_active
    role_or_status_changed = bool({"department_role", "is_active"} & changes)
    user.revision += 1
    user.updated_at = _now()
    if role_or_status_changed:
        revoke_user_sessions(db, user.id)
    if "department_role" in changes:
        _audit(db, request, principal, "USER_ROLE_CHANGED", "user", user.id, {"role": user.department_role})
    if "is_active" in changes:
        _audit(db, request, principal, "USER_ACTIVATED" if user.is_active else "USER_DEACTIVATED", "user", user.id)
    if not ({"department_role", "is_active"} & changes):
        _audit(db, request, principal, "USER_UPDATED", "user", user.id, {"fields": sorted(changes)})
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.post("/users/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_password(
    user_id: uuid.UUID,
    payload: PasswordResetRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_ready_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> PasswordResetResponse:
    user = _get_staff(db, user_id, lock=True)
    if not verify_password(payload.admin_password, principal.user.password_hash):
        raise api_error(status.HTTP_400_BAD_REQUEST, "ADMIN_PASSWORD_INVALID", "Mật khẩu Admin không đúng.")
    temporary_password = generate_token()
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    user.revision += 1
    user.updated_at = _now()
    revoke_user_sessions(db, user.id)
    _audit(db, request, principal, "PASSWORD_RESET", "user", user.id)
    db.commit()
    db.refresh(user)
    return PasswordResetResponse(user=_user_response(user), temporary_password=temporary_password)


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    principal: Annotated[Principal, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    actor_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=80),
    result: str | None = Query(default=None, max_length=20),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> AuditLogListResponse:
    del principal
    query = select(AuditLog).where(and_(
        AuditLog.actor_id == actor_id if actor_id else True,
        AuditLog.action == action if action else True,
        AuditLog.result == result if result else True,
        AuditLog.created_at >= created_from if created_from else True,
        AuditLog.created_at <= created_to if created_to else True,
    ))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    logs = db.scalars(query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    actor_ids = {item.actor_id for item in logs if item.actor_id is not None}
    actors = db.scalars(select(User).where(User.id.in_(actor_ids))).all() if actor_ids else []
    actor_names = {actor.id: actor.full_name for actor in actors}
    items = [AuditLogResponse(
        id=item.id,
        actor_id=item.actor_id,
        actor_name=actor_names.get(item.actor_id) if item.actor_id else None,
        action=item.action,
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        result=item.result,
        request_id=item.request_id,
        details=item.details or {},
        created_at=item.created_at,
    ) for item in logs]
    return AuditLogListResponse(items=items, page=page, page_size=page_size, total=total)
