import asyncio
import datetime
import json
import time
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.conversations.models import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageRequest,
    MessageResponse,
    ReferenceChunkResponse,
)
from db.database import get_db
from db.models import Conversation, User
from middlewares.auth import auth_middleware
from services.llm_service import Message, Role
from services.uni import LLM_MODEL, RAG_CHAT_ID, llm_service, rag_service

router = APIRouter(prefix="/conversations")

with open("prompts/related_questions.txt", "r", encoding="utf-8") as f:
    RELATED_QUESTIONS_PROMPT = f.read()
with open("prompts/title.txt", "r", encoding="utf-8") as f:
    TITLE_PROMPT = f.read()


def generate_related_questions(question: str) -> List[str]:
    try:
        messages = [
            Message(
                role=Role.SYSTEM,
                content=RELATED_QUESTIONS_PROMPT,
            ),
            Message(role=Role.USER, content=question),
        ]
        response = llm_service.chat(
            model=LLM_MODEL,
            messages=messages,
        )
        related_questions = response.content.split("\n")
        if isinstance(related_questions, list) and all(
            isinstance(q, str) for q in related_questions
        ):
            return related_questions
        else:
            return []
    except:
        return []


def generate_title(question: str) -> str:
    try:
        messages = [
            Message(
                role=Role.SYSTEM,
                content=TITLE_PROMPT,
            ),
            Message(role=Role.USER, content=question),
        ]
        response = llm_service.chat(
            model=LLM_MODEL,
            messages=messages,
        )
        title = response.content
        if isinstance(title, str):
            return title
        else:
            return "新会话"
    except:
        return "新会话"


async def update_conversation_title(
    user_id: uuid.UUID, conversation_id: uuid.UUID, title: str
):
    db = next(get_db())
    try:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if conversation:
            conversation.title = title
            db.commit()
    except:
        db.rollback()
    finally:
        db.close()


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    user: User = Depends(auth_middleware), db: Session = Depends(get_db)
):
    conversations = db.query(Conversation).filter(Conversation.user_id == user.id).all()
    return [
        ConversationResponse(
            id=str(conversation.id),
            title=conversation.title,
            created_at=str(conversation.created_at),
            updated_at=str(conversation.updated_at),
        )
        for conversation in conversations
    ]


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    user: User = Depends(auth_middleware), db: Session = Depends(get_db)
):
    try:
        conversation = Conversation(user_id=user.id, title="新会话")
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        rag_service.create_conversation(
            chat_id=RAG_CHAT_ID,
            user_id=str(user.id),
            conversation_id=str(conversation.id),
        )

        return ConversationResponse(
            id=str(conversation.id),
            title=conversation.title,
            created_at=str(conversation.created_at),
            updated_at=str(conversation.updated_at),
        )
    except:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(auth_middleware),
    db: Session = Depends(get_db),
):
    try:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == user.id,
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        messages = rag_service.get_conversation_messages(
            chat_id=RAG_CHAT_ID,
            user_id=str(user.id),
            conversation_id=str(conversation.id),
        )
        return ConversationDetailResponse(
            id=str(conversation.id),
            title=conversation.title,
            created_at=str(conversation.created_at),
            updated_at=str(conversation.updated_at),
            messages=[
                MessageResponse(
                    role=message.role,
                    content=message.content,
                    references=[
                        ReferenceChunkResponse(
                            id=reference.id,
                            content=reference.content,
                            dataset_id=reference.dataset_id,
                            document_id=reference.document_id,
                            document_name=reference.document_name,
                        )
                        for reference in message.references
                    ],
                )
                for message in messages
            ],
        )
    except HTTPException:
        raise
    except:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{conversation_id}", response_model=List[ConversationResponse])
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(auth_middleware),
    db: Session = Depends(get_db),
):

    try:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == user.id,
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        rag_service.delete_conversation(
            chat_id=RAG_CHAT_ID,
            user_id=str(user.id),
            conversation_id=str(conversation.id),
        )

        db.delete(conversation)
        db.commit()

        conversations = (
            db.query(Conversation).filter(Conversation.user_id == user.id).all()
        )

        return [
            ConversationResponse(
                id=str(conversation.id),
                title=conversation.title,
                created_at=str(conversation.created_at),
                updated_at=str(conversation.updated_at),
            )
            for conversation in conversations
        ]
    except HTTPException:
        raise
    except:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/{conversation_id}/chat")
async def chat(
    message: MessageRequest,
    conversation_id: str,
    user: User = Depends(auth_middleware),
    db: Session = Depends(get_db),
):
    if not message.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )

    try:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == uuid.UUID(conversation_id),
                Conversation.user_id == user.id,
            )
            .first()
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        conversation.updated_at = datetime.datetime.now()
        db.commit()

        need_title_update = conversation.title == "新会话"

        async def event_stream():
            loop = asyncio.get_event_loop()
            related_questions_future = loop.run_in_executor(
                None, generate_related_questions, message.question
            )

            if need_title_update:
                title_future = loop.run_in_executor(
                    None, generate_title, message.question
                )

            generator, references, complete_message = rag_service.chat(
                chat_id=RAG_CHAT_ID,
                user_id=str(user.id),
                conversation_id=str(conversation.id),
                message=message.question,
            )

            prev_content = None
            prev_time = None
            while True:
                chunk = await loop.run_in_executor(None, next, generator, None)
                if chunk is None:
                    break

                current_time = time.time()
                if prev_content is not None:
                    content_blocks = [
                        prev_content[i : i + 2] for i in range(0, len(prev_content), 2)
                    ]
                    delta_time = current_time - prev_time
                    num_blocks = len(content_blocks)
                    if num_blocks > 1:
                        send_interval = delta_time / (num_blocks - 1)
                    else:
                        send_interval = 0

                    for i, blocks in enumerate(content_blocks):
                        yield f"data: {json.dumps({"type": "content", "role": "assistant", "content": blocks})}\n\n"
                        if i < num_blocks - 1 and send_interval > 0:
                            await asyncio.sleep(send_interval)

                prev_content = chunk
                prev_time = current_time

            if prev_content is not None:
                content_blocks = [
                    prev_content[i : i + 2] for i in range(0, len(prev_content), 2)
                ]
                fixed_interval = 0.1
                for i, blocks in enumerate(content_blocks):
                    data = {
                        "type": "content",
                        "role": "assistant",
                        "content": blocks,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    if i < len(content_blocks) - 1 and fixed_interval > 0:
                        await asyncio.sleep(fixed_interval)

            if references and complete_message:
                data = {
                    "type": "finish",
                    "references": [reference.to_dict() for reference in references],
                    "complete_message": complete_message[0],
                }
                yield f"data: {json.dumps(data)}\n\n"

            related_questions = await related_questions_future
            data = {
                "type": "related_questions",
                "related_questions": related_questions,
            }
            yield f"data: {json.dumps(data)}\n\n"

            if need_title_update and title_future:
                title = await title_future
                data = {
                    "type": "title",
                    "title": title,
                }
                yield f"data: {json.dumps(data)}\n\n"
                await update_conversation_title(user.id, conversation.id, title)

        return StreamingResponse(
            content=event_stream(),
            media_type="text/event-stream",
        )
    except HTTPException:
        raise
    except:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
