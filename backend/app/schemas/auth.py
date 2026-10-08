import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")   # Từ chối các trường được thêm vào mà ko được khai báo


class LoginRequest(StrictModel):    # Vì LoginRequest kế thừa StrictModel, nên nếu ta khởi tạo LoginRequest mà truyền vào thừa tham số --> Forbid 
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    employee_code: str | None
    job_title: str | None
    account_type: str
    department_role: str | None
    department_id: int | None
    is_active: bool
    must_change_password: bool
    revision: int
    created_at: datetime


class LoginResponse(BaseModel):
    user: UserResponse


class CsrfResponse(BaseModel):
    csrf_token: str
