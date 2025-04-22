from typing import List

from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ReferenceChunkResponse(BaseModel):
    id: str
    content: str
    dataset_id: str
    document_id: str
    document_name: str


class MessageResponse(BaseModel):
    role: str
    content: str
    references: List[ReferenceChunkResponse]


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse]


class MessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
