from datetime import datetime
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints


class ChatSource(BaseModel):
    number: int
    document_id: str | None = None
    title: str | None = None
    section_path: str | list[str] | None = None


class ChatMessageRequest(BaseModel):
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: str
    content: str
    sources: list[ChatSource]
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[ChatMessageResponse]


class ChatTurnResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
