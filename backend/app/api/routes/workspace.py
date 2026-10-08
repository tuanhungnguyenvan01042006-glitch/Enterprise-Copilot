from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.auth import Principal, require_staff, validate_csrf
from app.core.errors import api_error
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.document_bookmark import DocumentBookmark
from app.models.note import Note
from app.models.task import Task
from app.schemas.workspace import (
    BookmarkResponse,
    NoteCreateRequest,
    NoteResponse,
    NoteUpdateRequest, 
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
)

router = APIRouter(prefix="/me", tags=["workspace"])


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


def _staff(principal: Principal) -> None:
    if principal.user.account_type != "STAFF" or principal.user.department_id is None:
        raise api_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Chức năng này chỉ dành cho nhân viên.")


def _task_scope(principal: Principal):
    return or_(
        (Task.kind == "PERSONAL") & (Task.created_by == principal.user.id),
        (Task.kind == "ASSIGNED") & (Task.assignee_id == principal.user.id),
    )

 # Hàm để chuyển Task (model) --> TaskResponse (Schema Response)
def _task(task: Task) -> TaskResponse:
    return TaskResponse.model_validate(task)  # model_validate là hàm thuộc class StrictModel, nó sẽ đọc dữ liệu input (task) --> Chuyển thành schema

# hàm cập nhật task nếu nó complete 
def _apply_completion(task: Task, new_status: str) -> None:
    task.status = new_status
    task.completed_at = _now() if new_status == "DONE" else None

# *NOTE : Giải thích luồng hoạt động của 1 route API end point  : 
"""
Request sẽ được gửi đến đúng Route dựa trên địa chỉ URL
Sau đó Request được đi qua Hàm xử lý của Route đó : 
+ Hàm này đảm nhận toàn bộ nhiệm vụ : Middleware(kiểm tra quyền), Controller (thao tác với DB), Service,...
+ Đặc biệt hàm này nhận vào rất nhiều tham số, và các tham số nà được lấy từ 2 nguồn chủ yếu : các hàm auth và Querr string trên URL 
"""

@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    principal: Annotated[Principal, Depends(require_staff)],  # Nếu có hàm Depends, có nghĩa là tham số này sẽ được gán bằng kết quả function hàm bên trong Depends
    # Nhắc lại : hàm require_staff vừa dùng để kiểm tra quyền,vừa trả về principal
    db: Annotated[Session, Depends(get_db)],
    kind: str | None = Query(default=None),   # Lấy từ Querry string trong URL 
    task_status: Annotated[str | None, Query(alias="status")] = None,
    priority: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=160),
) -> list[TaskResponse]:
    # BODY của 1 hàm Route : 
    # phần đầu là Middleware : Kiểm tra quyền,...
    _staff(principal)   # Vậy chức năng này dành cho cả nhân viên và sếp
    query = select(Task).where(Task.department_id == principal.user.department_id, Task.deleted_at.is_(None), _task_scope(principal))
    for column, value in ((Task.kind, kind), (Task.status, task_status), (Task.priority, priority)):
        if value:
            query = query.where(column == value)
    if q and q.strip():
        query = query.where(Task.title.ilike(f"%{q.strip()}%"))
    query = query.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.updated_at.desc())
    return [_task(item) for item in db.scalars(query).all()]


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskResponse:
    _staff(principal)
    title = payload.title.strip()
    if not title:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
    task = Task(
        department_id=principal.user.department_id,
        kind="PERSONAL",
        title=title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        assignee_id=principal.user.id,
        created_by=principal.user.id,
        completed_at=_now() if payload.status == "DONE" else None,
    )
    db.add(task)
    db.flush()
    _audit(db, request, principal, "PERSONAL_TASK_CREATED", "task", task.id, {"kind": "PERSONAL"})
    db.commit()
    db.refresh(task)
    return _task(task)


def _get_task(db: Session, principal: Principal, task_id: uuid.UUID) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None), Task.department_id == principal.user.department_id, _task_scope(principal)))
    if task is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy công việc.")
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, principal: Annotated[Principal, Depends(require_staff)], db: Annotated[Session, Depends(get_db)]) -> TaskResponse:
    _staff(principal)
    return _task(_get_task(db, principal, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> TaskResponse:
    _staff(principal)
    task = _get_task(db, principal, task_id)
    changes = payload.model_fields_set - {"expected_revision"}
    if not changes:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Cần có ít nhất một trường cần cập nhật.")
    if task.revision != payload.expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Dữ liệu đã được cập nhật. Vui lòng tải lại trước khi lưu.")
    if task.kind == "ASSIGNED":
        if changes != {"status"}:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "ASSIGNED_FIELDS_FORBIDDEN", "Bạn chỉ được cập nhật trạng thái công việc được giao.")
        allowed = {("TODO", "IN_PROGRESS"), ("IN_PROGRESS", "TODO"), ("TODO", "DONE"), ("IN_PROGRESS", "DONE")}
        if (task.status, payload.status) not in allowed:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_STATUS_TRANSITION", "Trạng thái công việc không hợp lệ.")
        _apply_completion(task, payload.status)
    else:
        if "title" in changes:
            title = (payload.title or "").strip()
            if not title:
                raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
            task.title = title
        if "description" in changes:
            task.description = payload.description
        if "priority" in changes:
            task.priority = payload.priority
        if "due_date" in changes:
            task.due_date = payload.due_date
        if "status" in changes:
            _apply_completion(task, payload.status)
    task.revision += 1
    task.updated_at = _now()
    _audit(db, request, principal, "TASK_UPDATED", "task", task.id, {"kind": task.kind, "fields": sorted(changes)})
    db.commit()
    db.refresh(task)
    return _task(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
    expected_revision: int = Query(ge=1),
) -> Response:
    _staff(principal)
    task = _get_task(db, principal, task_id)
    if task.kind != "PERSONAL":
        raise api_error(status.HTTP_403_FORBIDDEN, "ASSIGNED_DELETE_FORBIDDEN", "Công việc được giao không thể bị xóa.")
    if task.revision != expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Dữ liệu đã được cập nhật. Vui lòng tải lại trước khi xóa.")
    task.deleted_at = _now()
    task.revision += 1
    task.updated_at = _now()
    _audit(db, request, principal, "PERSONAL_TASK_DELETED", "task", task.id, {"kind": "PERSONAL"})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _note(note: Note) -> NoteResponse:
    return NoteResponse.model_validate(note)


def _get_note(db: Session, principal: Principal, note_id: uuid.UUID) -> Note:
    note = db.scalar(select(Note).where(Note.id == note_id, Note.owner_id == principal.user.id))
    if note is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy ghi chú.")
    return note


@router.get("/notes", response_model=list[NoteResponse])
def list_notes(
    principal: Annotated[Principal, Depends(require_staff)],
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, max_length=160),
) -> list[NoteResponse]:
    _staff(principal)
    query = select(Note).where(Note.owner_id == principal.user.id)
    if q and q.strip():
        query = query.where(Note.title.ilike(f"%{q.strip()}%"))
    return [_note(item) for item in db.scalars(query.order_by(Note.updated_at.desc())).all()]


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> NoteResponse:
    _staff(principal)
    title = payload.title.strip()
    if not title:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
    note = Note(owner_id=principal.user.id, title=title, content=payload.content)
    db.add(note)
    db.flush()
    _audit(db, request, principal, "PRIVATE_NOTE_CREATED", "note", note.id)
    db.commit()
    db.refresh(note)
    return _note(note)


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: uuid.UUID, principal: Annotated[Principal, Depends(require_staff)], db: Annotated[Session, Depends(get_db)]) -> NoteResponse:
    _staff(principal)
    return _note(_get_note(db, principal, note_id))


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> NoteResponse:
    _staff(principal)
    note = _get_note(db, principal, note_id)
    changes = payload.model_fields_set - {"expected_revision"}
    if not changes:
        raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Cần có ít nhất một trường cần cập nhật.")
    if note.revision != payload.expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Dữ liệu đã được cập nhật. Vui lòng tải lại trước khi lưu.")
    if "title" in changes:
        title = (payload.title or "").strip()
        if not title:
            raise api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", "Tiêu đề không được để trống.")
        note.title = title
    if "content" in changes:
        note.content = payload.content or ""
    note.revision += 1
    note.updated_at = _now()
    _audit(db, request, principal, "PRIVATE_NOTE_UPDATED", "note", note.id)
    db.commit()
    db.refresh(note)
    return _note(note)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: uuid.UUID,
    request: Request,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
    expected_revision: int = Query(ge=1),
) -> Response:
    _staff(principal)
    note = _get_note(db, principal, note_id)
    if note.revision != expected_revision:
        raise api_error(status.HTTP_409_CONFLICT, "REVISION_CONFLICT", "Dữ liệu đã được cập nhật. Vui lòng tải lại trước khi xóa.")
    _audit(db, request, principal, "PRIVATE_NOTE_DELETED", "note", note.id)
    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _readable_document(principal: Principal):
    scope = or_(
        Document.knowledge_scope == "COMPANY",
        (Document.knowledge_scope == "DEPARTMENT") & (Document.department_id == principal.user.department_id),
    )
    return (scope,)

@router.get("/bookmarks", response_model=list[BookmarkResponse])
def list_bookmarks(principal: Annotated[Principal, Depends(require_staff)], db: Annotated[Session, Depends(get_db)]) -> list[BookmarkResponse]:
    _staff(principal)
    query = select(DocumentBookmark, Document).join(Document, Document.id == DocumentBookmark.document_id).where(
        DocumentBookmark.user_id == principal.user.id, *_readable_document(principal)
    ).order_by(Document.updated_at.desc())
    return [BookmarkResponse(document_id=document.id, title=document.title, category=document.category, updated_at=document.updated_at) for _, document in db.execute(query).all()]


@router.put("/bookmarks/{document_id}", response_model=BookmarkResponse)
def add_bookmark(
    document_id: uuid.UUID,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> BookmarkResponse:
    _staff(principal)
    document = db.scalar(select(Document).where(Document.id == document_id, *_readable_document(principal)))
    if document is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND", "Không tìm thấy tài liệu.")
    existing = db.get(DocumentBookmark, {"user_id": principal.user.id, "document_id": document.id})
    if existing is None:
        db.add(DocumentBookmark(user_id=principal.user.id, document_id=document.id))
        db.commit()
    return BookmarkResponse(document_id=document.id, title=document.title, category=document.category, updated_at=document.updated_at)


@router.delete("/bookmarks/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    document_id: uuid.UUID,
    principal: Annotated[Principal, Depends(validate_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _staff(principal)
    db.execute(delete(DocumentBookmark).where(DocumentBookmark.user_id == principal.user.id, DocumentBookmark.document_id == document_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
