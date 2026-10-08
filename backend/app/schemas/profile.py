from pydantic import Field

from app.schemas.auth import StrictModel, UserResponse


class ProfileUpdateRequest(StrictModel):
    full_name: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(ge=1)


class ProfileResponse(UserResponse):
    department_name: str | None = None
