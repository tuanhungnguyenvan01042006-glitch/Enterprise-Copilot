import hashlib
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_ready_principal, validate_csrf
from app.core.config import get_settings
from app.core.errors import api_error
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import User
from app.RAG.pipeline import index_uploaded_document
from app.schemas.document import (
    DocumentFileResponse,
    DocumentListResponse,
    DocumentMetadata,
    DocumentPermissions,
    DocumentResponse,
    DocumentUpdateRequest,
)

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
}
PREVIEW_LIMIT = 100 * 1024


def _storage_root() -> Path:
    root = get_settings().upload_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_path(storage_key: str) -> Path:
    root = _storage_root()
    path = (root / storage_key).resolve()
    if root != path and root not in path.parents:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy tệp.")
    return path


def _document_scope(principal: Principal):
    user = principal.user
    if user.account_type == "ADMIN":
        return ()
    scope = or_(
        Document.knowledge_scope == "COMPANY",
        (Document.knowledge_scope == "DEPARTMENT") & (Document.department_id == user.department_id),
    )
    return (scope,)


def _can_manage(principal: Principal, document: Document | None = None) -> bool:
    user = principal.user
    if user.account_type == "ADMIN":
        return True
    return bool(
        user.account_type == "STAFF"
        and user.department_role == "MANAGER"
        and user.department_id is not None
        and document is not None
        and document.knowledge_scope == "DEPARTMENT"
        and document.department_id == user.department_id
    )


def _require_manager_or_admin(principal: Principal) -> None:
    if principal.user.account_type != "ADMIN" and principal.user.department_role != "MANAGER":
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Chức năng này chỉ dành cho quản lý hoặc quản trị viên.")


def _audit(db: Session, request: Request, principal: Principal, action: str, document_id: uuid.UUID, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_id=principal.user.id,
        action=action,
        entity_type="document",
        entity_id=str(document_id),
        result="SUCCESS",
        request_id=getattr(request.state, "request_id", "unknown"),
        details=details or {},
    ))


def _file_response(document: Document) -> DocumentFileResponse:
    return DocumentFileResponse(
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        checksum_sha256=document.checksum_sha256,
        uploaded_by=document.uploaded_by,
        uploaded_at=document.uploaded_at,
    )


def _response(db: Session, principal: Principal, document: Document) -> DocumentResponse:
    creator = db.get(User, document.created_by)
    updater = db.get(User, document.updated_by)
    return DocumentResponse(
        id=document.id,
        knowledge_scope=document.knowledge_scope,
        department_id=document.department_id,
        title=document.title,
        description=document.description,
        category=document.category,
        language=document.language,
        created_by=document.created_by,
        updated_by=document.updated_by,
        creator_name=creator.full_name if creator else None,
        updater_name=updater.full_name if updater else None,
        revision=document.revision,
        created_at=document.created_at,
        updated_at=document.updated_at,
        file=_file_response(document),
        permissions=DocumentPermissions(
            can_edit=_can_manage(principal, document),
            can_upload_file=_can_manage(principal, document),
            can_bookmark=principal.user.account_type == "STAFF",
        ),
    )


def _get_readable(db: Session, principal: Principal, document_id: uuid.UUID) -> Document:
    document = db.scalar(select(Document).where(Document.id == document_id, *_document_scope(principal)))
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.")
    return document


def _validate_metadata(metadata: DocumentMetadata, principal: Principal) -> DocumentMetadata:
    data = metadata.model_copy(update={"title": metadata.title.strip(), "description": metadata.description.strip() if metadata.description else None})
    if not data.title:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
    if data.knowledge_scope == "COMPANY":
        if data.department_id is not None:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tài liệu Company không được gắn phòng ban.")
    elif data.department_id is None:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tài liệu Department phải có phòng ban.")
    if principal.user.account_type != "ADMIN":
        if data.knowledge_scope != "DEPARTMENT" or data.department_id != principal.user.department_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Quản lý chỉ được quản lý tài liệu phòng ban của mình.")
    return data 


def _validate_upload(upload: UploadFile) -> str:
    filename = Path(upload.filename or "").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise api_error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_FILE_TYPE", "Chỉ chấp nhận PDF, MD hoặc TXT.")
    if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES[extension]:
        raise api_error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_FILE_TYPE", "Định dạng tệp không khớp phần mở rộng.")
    return extension


def _stage_upload(upload: UploadFile, extension: str) -> tuple[Path, int, str]:
    root = _storage_root()
    temp_dir = root / ".tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    fd, raw_path = tempfile.mkstemp(prefix="document-", suffix=extension, dir=temp_dir)
    os.close(fd)
    path = Path(raw_path)
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("wb") as target:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise api_error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "FILE_TOO_LARGE", "Tệp vượt quá dung lượng cho phép.")
                digest.update(chunk)
                target.write(chunk)
        if total == 0:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tệp không được rỗng.")
        return path, total, digest.hexdigest()
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _finalize(
    staged: Path,
    document_id: uuid.UUID,
    file_token: uuid.UUID,
    knowledge_scope: str,
    department_id: int | None,
    extension: str,
) -> tuple[str, Path]:
    if knowledge_scope == "COMPANY":
        key = f"COMPANY/{document_id}/{file_token}{extension}"   
    else:
        key = f"DEPARTMENT/{department_id}/{document_id}/{file_token}{extension}"
    final_path = _safe_path(key)   
    final_path.parent.mkdir(parents=True, exist_ok=True)
    staged.replace(final_path)
    return key, final_path




def _parse_metadata(raw: str) -> DocumentMetadata:
    try:
        return DocumentMetadata.model_validate_json(raw)
    except ValidationError as exc:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Metadata tài liệu không hợp lệ.", exc.errors()) from exc


@router.get("", response_model=DocumentListResponse)
def list_documents(
    principal: Annotated[Principal, Depends(require_ready_principal)],
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    knowledge_scope: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DocumentListResponse:
    query = select(Document).where(*_document_scope(principal))
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(or_(Document.title.ilike(term), Document.description.ilike(term)))
    if category:
        query = query.where(Document.category == category)
    if language:
        query = query.where(Document.language == language)
    if knowledge_scope:
        query = query.where(Document.knowledge_scope == knowledge_scope)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    documents = db.scalars(query.order_by(Document.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return DocumentListResponse(items=[_response(db, principal, item) for item in documents], page=page, page_size=page_size, total=total)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    background_tasks: BackgroundTasks,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
    metadata: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    _require_manager_or_admin(principal)
    parsed = _validate_metadata(_parse_metadata(metadata), principal)
    extension = _validate_upload(file)
    staged, size, checksum = _stage_upload(file, extension)
    # hàm này trả về Staged : địa chỉ lưu file tạm 
    final_path: Path | None = None        # khai báo biến final_path
    original_filename = Path(file.filename or f"document{extension}").name[:255]
    # lấy ra tên file, từ file.filename
    mime_type = file.content_type or ("application/pdf" if extension == ".pdf" else "text/plain")
    document = Document(
        # ko hề có Document_id 
        knowledge_scope=parsed.knowledge_scope,
        department_id=parsed.department_id,
        title=parsed.title,
        description=parsed.description,
        category=parsed.category,
        language=parsed.language,
        created_by=principal.user.id,
        updated_by=principal.user.id,
        original_filename=original_filename,
        storage_key=f"pending/{uuid.uuid4()}",  # storage key : là địa chỉ storage (địa chỉ lưu file trên backend), ở đây nó tạm thời gắn với với 1 khóa tạm 
        # bởi hiện tại file chx đc đẩy lên chính thức địa chỉ Cuối cùng, khi chạy hàm finalize() thành công, trả về storage key, thì mới sửa lại thành địa chỉ thực
        mime_type=mime_type,
        size_bytes=size,
        checksum_sha256=checksum,
        uploaded_by=principal.user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    committed = False
    try:
        db.add(document)
        db.flush()
        # hàm flush gọi SQLAIchemy tạo Document_id... :Đặc biệt , Document_id chỉ được tạo sau khi đã add xong Document đó vào table
        key, final_path = _finalize(staged, document.id, uuid.uuid4(), document.knowledge_scope, document.department_id, extension)
        # hàm finalize() chép nội dung file sang địa chỉ đích, ngoài ra nó trả về storage key (Company/...), và Path : trỏ tới địa chỉ thực của file
        document.storage_key = key
        # 1 điêm khá lạ là, đối với đối tượng Document vừa mới add vào Database 
        _audit(db, request, principal, "DOCUMENT_CREATED", document.id, {"filename": original_filename})
        db.commit()
        committed = True
        db.refresh(document)
        if final_path is not None:
            background_tasks.add_task(        # Background tasks là thư viện hỗ trợ chạy hàm bất đồng biến (assync) trong fastAPI
                index_uploaded_document,
                final_path,
                document_id=document.id,
                knowledge_scope=document.knowledge_scope,
                department_id=document.department_id,
                title=document.title,
                category=document.category,
                storage_key=document.storage_key,
            )
        return _response(db, principal, document)
    except Exception:
        staged.unlink(missing_ok=True)
        if final_path and not committed:
            final_path.unlink(missing_ok=True)
        db.rollback()
        raise


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, principal: Annotated[Principal, Depends(require_ready_principal)], db: Annotated[Session, Depends(get_db)]) -> DocumentResponse:
    return _response(db, principal, _get_readable(db, principal, document_id))


# Hàm cập nhật metadatas : Giúp Admin có thể cập nhật Metadata theo ý muốn
@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    _require_manager_or_admin(principal)   # Đòi hỏi quyền Manager,Admin
    document = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
    # Lấy ra tài liệu cần cập nhật(select), và dùng with_for_update để khóa tài liệu, tránh việc cập nhật đồng thời 

    if document is None or not _can_manage(principal, document): # Can manage là hàm kiểm tra quyền : admin quản lý tài liệu company, manager qly tài liệu department
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.")
    if document.revision != payload.expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Tài liệu đã được cập nhật. Vui lòng tải lại.")
    changes = payload.model_fields_set - {"expected_revision"}
    # Changes là những trường cần cập nhật 
    if not changes:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Cần có ít nhất một trường cần cập nhật.")
    values = payload.model_dump(exclude={"expected_revision"}, exclude_unset=True)
    # lấy ra giá trị các trường cần cập nhật 
    previous_scope = document.knowledge_scope
    candidate_scope = values.get("knowledge_scope", document.knowledge_scope)
    candidate_department = values.get("department_id", document.department_id)
    if candidate_scope == "COMPANY" and "department_id" not in values:
        candidate_department = None
    # tạo ra candidate (thông tin cập nhật),và validate nó trước khi add vào DB 
    candidate = _validate_metadata(
        DocumentMetadata(
            title=values.get("title", document.title),
            description=values.get("description", document.description),
            category=values.get("category", document.category),
            knowledge_scope=candidate_scope,
            language=values.get("language", document.language),
            department_id=candidate_department,
        ),
        principal,
    )
    for field in ("title", "description", "category", "knowledge_scope", "language", "department_id"):
        setattr(document, field, getattr(candidate, field))   # Đây chính là hàm cập nhật giá trị trong DB 
    document.updated_by = principal.user.id
    document.updated_at = datetime.now(timezone.utc)
    document.revision += 1
    _audit(db, request, principal, "DOCUMENT_UPDATED", document.id, {"fields": sorted(changes)})
    if "knowledge_scope" in changes and previous_scope != document.knowledge_scope:
        _audit(db, request, principal, "DOCUMENT_VISIBILITY_CHANGED", document.id, {"from": previous_scope, "to": document.knowledge_scope})
    db.commit()
    db.refresh(document)
    return _response(db, principal, document)

# Hàm thay file của 1 Document có sẵn 
@router.post("/{document_id}/file", response_model=DocumentResponse)
def upload_file(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
    expected_revision: Annotated[int, Form()],
    file: Annotated[UploadFile, File()],
    # Nhận vào file mới , ngoài ra chỉ cần nhận vào thêm Document ID và Revision
) -> DocumentResponse:
    extension = _validate_upload(file)
    staged, size, checksum = _stage_upload(file, extension) # Lưu file ở địa chỉ tạm 
    final_path: Path | None = None
    old_storage_key: str | None = None
    original_filename = Path(file.filename or f"document{extension}").name[:255]
    mime_type = file.content_type or ("application/pdf" if extension == ".pdf" else "text/plain")
    committed = False
    try:
        document = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
        if document is None or not _can_manage(principal, document):
            raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.")
        if document.revision != expected_revision:
            raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Tài liệu đã được cập nhật. Vui lòng tải lại.")
        old_storage_key = document.storage_key
        key, final_path = _finalize(staged, document.id, uuid.uuid4(), document.knowledge_scope, document.department_id, extension)
        document.original_filename = original_filename
        document.storage_key = key
        document.mime_type = mime_type
        document.size_bytes = size
        document.checksum_sha256 = checksum
        document.uploaded_by = principal.user.id
        document.uploaded_at = datetime.now(timezone.utc)
        document.updated_by = principal.user.id
        document.updated_at = datetime.now(timezone.utc)
        document.revision += 1
        _audit(db, request, principal, "DOCUMENT_FILE_REPLACED", document.id, {"filename": original_filename})
        db.commit()
        committed = True
        db.refresh(document)
    except Exception:
        staged.unlink(missing_ok=True)
        if final_path and not committed:
            final_path.unlink(missing_ok=True)
        db.rollback()
        raise

    if old_storage_key and old_storage_key != document.storage_key:
        try:
            _safe_path(old_storage_key).unlink(missing_ok=True)
        except OSError:
            pass
    if final_path is not None:
        background_tasks.add_task(
            index_uploaded_document,
            final_path,
            document_id=document.id,
            knowledge_scope=document.knowledge_scope,
            department_id=document.department_id,
            title=document.title,
            category=document.category,
            storage_key=document.storage_key,
        )
    return _response(db, principal, document)
# Hàm này sẽ cần gọi hàm logic xử lý khi thay file ở Qdrant 


@router.get("/{document_id}/file/download")
def download_file(document_id: uuid.UUID, principal: Annotated[Principal, Depends(require_ready_principal)], db: Annotated[Session, Depends(get_db)]) -> FileResponse:
    document = _get_readable(db, principal, document_id)
    path = _safe_path(document.storage_key)
    if not path.is_file():
        raise api_error(status.HTTP_404_NOT_FOUND, "FILE_NOT_FOUND", "Không tìm thấy tệp lưu trữ.")
    return FileResponse(path, media_type=document.mime_type, filename=document.original_filename, headers={"X-Content-Type-Options": "nosniff"})


@router.get("/{document_id}/file/preview")
def preview_file(document_id: uuid.UUID, principal: Annotated[Principal, Depends(require_ready_principal)], db: Annotated[Session, Depends(get_db)]) -> PlainTextResponse:
    document = _get_readable(db, principal, document_id)
    if Path(document.original_filename).suffix.lower() not in {".md", ".txt"}:
        raise api_error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "PREVIEW_UNSUPPORTED", "Chỉ hỗ trợ preview MD/TXT.")
    path = _safe_path(document.storage_key)
    try:
        content = path.read_bytes()[:PREVIEW_LIMIT].decode("utf-8")
    except FileNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "FILE_NOT_FOUND", "Không tìm thấy tệp lưu trữ.") from exc
    except UnicodeDecodeError as exc:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_UTF8", "Tệp không phải UTF-8 hợp lệ.") from exc
    return PlainTextResponse(content, headers={"X-Content-Type-Options": "nosniff"})
