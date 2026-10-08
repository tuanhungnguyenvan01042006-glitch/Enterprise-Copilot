from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_principal, revoke_user_sessions, validate_csrf
from app.core.config import get_settings
from app.core.errors import api_error
from app.core.login_throttle import login_throttle
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, CsrfResponse, LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def public_user(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def _delete_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,      # chuẩn hóa đầu vào Paload phải đúng dạng Login Request
    request: Request,           # chưa hiểu tham số Request, Response ở đây lấy ở đâu, do chưa hề import vào 
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:         # Chuẩn hóa đầu ra 
    settings = get_settings()
    email = payload.email.strip().lower()
    ip_address = request.client.host if request.client else "unknown"

    if login_throttle.is_blocked(email, ip_address):
        raise api_error(status.HTTP_429_TOO_MANY_REQUESTS, "LOGIN_THROTTLED", "Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau.")

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        login_throttle.record_failure(email, ip_address)
        db.add(AuditLog(
            actor_id=None,
            action="LOGIN_FAILED",
            entity_type="user",
            entity_id=str(user.id) if user else None,
            result="FAILURE",
            request_id=getattr(request.state, "request_id", "unknown"),
            details={},
        ))
        db.commit()
        raise api_error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng.")

    login_throttle.record_success(email)
    raw_token = generate_token()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token=generate_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(auth_session)
    db.add(AuditLog(
        actor_id=user.id,
        action="LOGIN_SUCCEEDED",
        entity_type="user",
        entity_id=str(user.id),
        result="SUCCESS",
        request_id=getattr(request.state, "request_id", "unknown"),
        details={},
    ))
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_hours * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return LoginResponse(user=public_user(user))


@router.get("/me", response_model=UserResponse)
def me(principal: Annotated[Principal, Depends(require_principal)]) -> UserResponse:
    return public_user(principal.user)


@router.get("/csrf", response_model=CsrfResponse)
def csrf(principal: Annotated[Principal, Depends(require_principal)]) -> CsrfResponse:
    return CsrfResponse(csrf_token=principal.session.csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    principal.session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    _delete_session_cookie(response)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    user = principal.user
    if not verify_password(payload.current_password, user.password_hash):
        raise api_error(status.HTTP_400_BAD_REQUEST, "CURRENT_PASSWORD_INVALID", "Mật khẩu hiện tại không đúng.")
    if verify_password(payload.new_password, user.password_hash):
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "PASSWORD_UNCHANGED", "Mật khẩu mới phải khác mật khẩu hiện tại.")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.revision += 1
    user.updated_at = datetime.now(timezone.utc)
    revoke_user_sessions(db, user.id)
    db.commit()
    _delete_session_cookie(response)
