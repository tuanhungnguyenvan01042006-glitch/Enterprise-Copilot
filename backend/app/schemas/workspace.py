"""
* Nhắc lại vai trò : 
+ Schema có nhiệm vụ đưa dữ liệu Input (vào Route) và Output (về FE) về dạng chuẩn 
+ Ở đây, file này định nghĩa schema dữ liệu (các class) cho các chức năng Workspace 
+ Bản chất Schema : Chính là định nghĩa (các trường dữ liệu) Request (input) và Response (output) của 1 Chức năng
+ Đó là sự khác biệt với model : là dữ liệu được lưu thực tế ở DB, còn schema chỉ là class (cấu trúc dữ liệu)
"""

from datetime import date, datetime
from typing import Literal
import uuid

from pydantic import Field

from app.schemas.auth import StrictModel   # StrictModel là lớp Pydantic, dùng để tạo chema kiểm soát đầu vào 

TaskKind = Literal["PERSONAL", "ASSIGNED"]
TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE", "CANCELLED"]
TaskPriority = Literal["LOW", "NORMAL", "HIGH"]



# Các class này đều là các class Request, chính là input vào cho các chức năng của workspace 
# Vậy triết lý là : Khi xây dựng 1 tính năng, ta sẽ nhận Input vào là 1 Request, và đối với từng chức năng, thì Request này sẽ cần chứa những thông tin cố định, ko được thừa.
class TaskCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    status: TaskStatus = "TODO"
    priority: TaskPriority = "NORMAL"
    due_date: date | None = None


class TaskUpdateRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class TaskResponse(StrictModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    department_id: int
    kind: TaskKind
    title: str 
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: uuid.UUID
    created_by: uuid.UUID
    due_date: date | None
    completed_at: datetime | None
    revision: int
    created_at: datetime
    updated_at: datetime


class NoteCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(max_length=20000)


class NoteUpdateRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, max_length=20000)


class NoteResponse(StrictModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    content: str
    revision: int
    created_at: datetime
    updated_at: datetime


class BookmarkResponse(StrictModel):
    document_id: uuid.UUID
    title: str
    category: str
    updated_at: datetime


class DepartmentMemberResponse(StrictModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    full_name: str
    email: str
    employee_code: str
    job_title: str | None
    department_role: Literal["EMPLOYEE", "MANAGER"]
    is_active: bool


class DepartmentTaskCreateRequest(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    assignee_id: uuid.UUID
    priority: TaskPriority = "NORMAL"
    due_date: date | None = None


class DepartmentTaskUpdateRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    assignee_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class DepartmentTaskResponse(TaskResponse):
    assignee: DepartmentMemberResponse
    creator: DepartmentMemberResponse


class DepartmentMemberListResponse(StrictModel):
    items: list[DepartmentMemberResponse]
    page: int
    page_size: int
    total: int


class DepartmentTaskListResponse(StrictModel):
    items: list[DepartmentTaskResponse]
    page: int
    page_size: int
    total: int

