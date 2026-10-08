"""
File này là trung tâm xác thực và phân quyền của backend FastAPI.
 Nó trả lời hai câu hỏi:
Người gửi request có đăng nhập hợp lệ không?
Người đó có quyền thực hiện thao tác này không?
Có thể xem file này như một lớp bảo vệ đứng trước các API cần đăng nhập.

* File này rất quan trọng ở chỗ, gần như mọi API xử lý ở Backend (route), thì đều cần 
xác thực User, quyền (staff/admin), hoặc bảo mật (csrf). Hơn nữa, các hàm này sẽ trả về biến Principal (thông tin người dùng)

--> Có thể coi file này như Middleware (trong mảng Auth : xác thực quyền (ticket))
"""
# Tức là có 1 số API ( Thao tác) yêu cầu quyền (Ticket) để thực hiện : Tức là người dùng phải sở hữu quyền thực hiện nó 
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Callable

from fastapi import Depends, Request, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import api_error
from app.core.security import hash_token
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
 

@dataclass(frozen=True)
class Principal:        # Người dùng hiện tạ,sau khi xác thực thành công 
    session: AuthSession 
    user: User

# Các Route (API Endpoint) có thể dùng princpal.user để xác định danh tính và quyền user 
# Vậy class Principal (bên trong core/auth) đảm nhận nhiệm vụ giúp Route xác định user thực hiện request : bao gồm quyền, danh tính 


 # Hàm này có nhiệm vụ xác định / lấy ra Principal (người dùng hiện tại) từ việc đối chiếu token trong Request với DB 
def resolve_principal(request: Request, db: Session) -> Principal | None:
    raw_token = request.cookies.get(get_settings().session_cookie_name)  # Lấy token từ request 
    if not raw_token:
        return None

    auth_session = db.scalar(      # db là 1 session : Kết nối tới database 
        select(AuthSession).where(
            AuthSession.token_hash == hash_token(raw_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    )   # Lấy ra Auth Session (1 bảng trong database lưu các thông tin định danh như user id, token, ...)
    if auth_session is None:
        return None

# từ auth session lấy được, ta dùng trường user.id để lấy ra toàn bộ thông tin User, thông qua truy vấn bảng User dựa trên user.id
    user = db.get(User, auth_session.user_id)
    if user is None or not user.is_active:
        if auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(timezone.utc)
            db.commit()
        return None
    return Principal(session=auth_session, user=user)


# Hàm trên đã lấy ra được người dùng hiện tại : Principal, 2 hàm dưới có nhiệm vụ xác thực người dùng hiện tại : Xác thực thông tin của principal có chuẩn chỉ không


def require_principal(request: Request, db: Annotated[Session, Depends(get_db)]) -> Principal:
    principal = resolve_principal(request, db)
    if principal is None:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED", "Phiên đăng nhập không còn hiệu lực.")
    return principal


def require_ready_principal(principal: Annotated[Principal, Depends(require_principal)]) -> Principal:
    if principal.user.must_change_password:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "PASSWORD_CHANGE_REQUIRED",
            "Bạn cần đổi mật khẩu trước khi tiếp tục.",
        )
    return principal

   # Gọi hàm này, nếu phát hiện người dùng ko có quyền truy cập 
def _forbid() -> None:
    raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Bạn không có quyền thực hiện thao tác này.")


def require_staff(principal: Annotated[Principal, Depends(require_ready_principal)]) -> Principal:
    if principal.user.account_type != "STAFF":
        _forbid()
    return principal


def require_manager(principal: Annotated[Principal, Depends(require_staff)]) -> Principal:
    if principal.user.department_role != "MANAGER":
        _forbid()
    return principal


def require_admin(principal: Annotated[Principal, Depends(require_ready_principal)]) -> Principal:
    if principal.user.account_type != "ADMIN":
        _forbid()
    return principal


def validate_csrf(
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> Principal:
    settings = get_settings()
    origin = request.headers.get("Origin")
    token = request.headers.get("X-CSRF-Token")
    if origin not in settings.allowed_origins_list or not token or not secrets_compare(token, principal.session.csrf_token):
        raise api_error(status.HTTP_403_FORBIDDEN, "CSRF_VALIDATION_FAILED", "Yêu cầu bảo mật không hợp lệ.")
    return principal


def validate_ready_csrf(
    request: Request,
    principal: Annotated[Principal, Depends(require_ready_principal)],
) -> Principal:
    settings = get_settings()
    origin = request.headers.get("Origin")
    token = request.headers.get("X-CSRF-Token")
    if origin not in settings.allowed_origins_list or not token or not secrets_compare(token, principal.session.csrf_token):
        raise api_error(status.HTTP_403_FORBIDDEN, "CSRF_VALIDATION_FAILED", "Yêu cầu bảo mật không hợp lệ.")
    return principal


def secrets_compare(left: str, right: str) -> bool:
    from secrets import compare_digest

    return compare_digest(left, right)


def revoke_user_sessions(db: Session, user_id: object) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )


RoleDependency = Callable[..., Principal]
