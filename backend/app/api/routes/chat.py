import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.RAG.service import answer_question
from app.core.auth import Principal, require_staff, validate_ready_csrf
from app.core.errors import api_error
from app.db.session import get_db
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatSource, ChatTurnResponse, ConversationDetail, ConversationResponse

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def owned_conversation(db: Session, principal: Principal, conversation_id: UUID, lock: bool = False) -> ChatConversation:
    query = select(ChatConversation).where(ChatConversation.id == conversation_id, ChatConversation.owner_id == principal.user.id)
    if lock:
        query = query.with_for_update()
    conversation = db.scalar(query)
    if conversation is None:
        raise api_error(404, "RESOURCE_NOT_FOUND", "Không tìm thấy cuộc hội thoại.")
    return conversation


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(principal: Annotated[Principal, Depends(require_staff)], db: Annotated[Session, Depends(get_db)]):
    return db.scalars(select(ChatConversation).where(ChatConversation.owner_id == principal.user.id).order_by(ChatConversation.updated_at.desc(), ChatConversation.id)).all()


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(principal: Annotated[Principal, Depends(require_staff)], csrf: Annotated[Principal, Depends(validate_ready_csrf)], db: Annotated[Session, Depends(get_db)]):
    conversation = ChatConversation(owner_id=principal.user.id, title="Cuộc hội thoại mới")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, principal: Annotated[Principal, Depends(require_staff)], db: Annotated[Session, Depends(get_db)]):
    conversation = owned_conversation(db, principal, conversation_id)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation.id).order_by(ChatMessage.created_at, ChatMessage.id)).all()
    return ConversationDetail(**ConversationResponse.model_validate(conversation).model_dump(), messages=[ChatMessageResponse.model_validate(m) for m in messages])


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, principal: Annotated[Principal, Depends(require_staff)], csrf: Annotated[Principal, Depends(validate_ready_csrf)], db: Annotated[Session, Depends(get_db)]):
    conversation = owned_conversation(db, principal, conversation_id, lock=True)
    db.delete(conversation)
    db.commit()
    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/messages", response_model=ChatTurnResponse, status_code=201)
def send_message(conversation_id: UUID, payload: ChatMessageRequest, request: Request, principal: Annotated[Principal, Depends(require_staff)], csrf: Annotated[Principal, Depends(validate_ready_csrf)], db: Annotated[Session, Depends(get_db)]):
    owned_conversation(db, principal, conversation_id)
    # Do not hold a database transaction while waiting for external services.
    db.rollback()
    try:
        result = answer_question(payload.content)
        if not isinstance(result.get("answer"), str) or not result["answer"].strip():
            raise ValueError("Empty RAG answer")
        sources = [ChatSource.model_validate(source).model_dump() for source in result.get("sources", [])]
    except Exception:
        logger.warning("Chat RAG request failed; request_id=%s", getattr(request.state, "request_id", "unknown"))
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "CHAT_SERVICE_UNAVAILABLE", "Không thể tạo câu trả lời lúc này. Vui lòng thử lại.") from None
    conversation = owned_conversation(db, principal, conversation_id, lock=True)
    now = datetime.now(timezone.utc)
    user_message = ChatMessage(conversation_id=conversation.id, role="user", content=payload.content, sources=[], created_at=now)
    assistant_message = ChatMessage(conversation_id=conversation.id, role="assistant", content=result["answer"], sources=sources, created_at=now + timedelta(microseconds=1))
    if conversation.title == "Cuộc hội thoại mới":
        conversation.title = payload.content[:160]
    conversation.updated_at = now
    db.add_all([user_message, assistant_message])
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return ChatTurnResponse(user_message=ChatMessageResponse.model_validate(user_message), assistant_message=ChatMessageResponse.model_validate(assistant_message))
