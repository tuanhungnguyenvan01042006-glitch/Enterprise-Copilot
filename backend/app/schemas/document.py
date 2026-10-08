from typing import Literal
import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.auth import StrictModel


DocumentCategory = Literal["POLICY", "SOP", "GUIDE", "REFERENCE"]
KnowledgeScope = Literal["COMPANY", "DEPARTMENT"]
DocumentLanguage = Literal["vi", "en", "other"]
class DocumentMetadata(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: DocumentCategory
    knowledge_scope: KnowledgeScope
    language: DocumentLanguage     # ko hiểu đoạn này, vì Knowledge Scope, DocumentLanguage,... đâu phải là 1 model, nên đâu có thể gán thế này
    department_id: int | None = None
  # Vậy, mặc dù đã có bảng model Document, nhưng ta vẫn cần tạo ra schema Document Metadata (tức là chỉ lấy 1 vài trường của Document gốc cho metadata)

class DocumentUpdateRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: DocumentCategory | None = None
    knowledge_scope: KnowledgeScope | None = None
    language: DocumentLanguage | None = None
    department_id: int | None = None


class DocumentFileResponse(StrictModel):
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime


class DocumentPermissions(StrictModel):
    can_edit: bool
    can_upload_file: bool
    can_bookmark: bool


class DocumentResponse(StrictModel):
    id: uuid.UUID
    knowledge_scope: KnowledgeScope
    department_id: int | None
    title: str
    description: str | None
    category: DocumentCategory
    language: DocumentLanguage
    created_by: uuid.UUID
    updated_by: uuid.UUID
    creator_name: str | None
    updater_name: str | None
    revision: int
    created_at: datetime
    updated_at: datetime
    file: DocumentFileResponse | None
    permissions: DocumentPermissions


class DocumentListResponse(StrictModel):
    items: list[DocumentResponse]
    page: int
    page_size: int
    total: int
