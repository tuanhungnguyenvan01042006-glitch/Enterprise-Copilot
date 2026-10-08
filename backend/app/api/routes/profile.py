from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_ready_principal, validate_csrf
from app.core.errors import api_error
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/me/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(principal: Annotated[Principal, Depends(require_ready_principal)]) -> ProfileResponse:
    return ProfileResponse.model_validate(principal.user)
# Ta có thể thấy, với mỗi hàm API, nó đều xác thực User (require_ready_principal), hoặc quyền, hoặc bảo mật
# thông qua hàm Depends(core/auth_function) : tức là chạy hàm auth để xác thực trước. Hàm xác thực sau đó lại trả về output chính là principal : Biến dùng để lưu thông tin user hiện tại 

@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ProfileResponse:
    if principal.user.must_change_password:
        raise api_error(status.HTTP_403_FORBIDDEN, "PASSWORD_CHANGE_REQUIRED", "Bạn cần đổi mật khẩu trước khi tiếp tục.")

    full_name = payload.full_name.strip()
    if not full_name:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Họ và tên không được để trống.")

    result = db.execute(
        update(User)
        .where(User.id == principal.user.id, User.revision == payload.expected_revision)
        .values(full_name=full_name, revision=User.revision + 1, updated_at=datetime.now(timezone.utc))
    )
    if result.rowcount != 1:
        db.rollback()
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Thông tin đã thay đổi. Vui lòng tải lại và thử lại.")
    db.commit()
    db.refresh(principal.user)
    return ProfileResponse.model_validate(principal.user)
