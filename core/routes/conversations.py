from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.domain.auth_model import CurrentUser
from core.domain.workflow_model import Conversation, Message, MessageCreate
from core.services.auth import PortalUser, require_roles
from core.services.db import get_db
from core.services.dependencies import StrapiDependency
from core.services.workflow import create_message, get_conversation, list_messages, open_conversation


router = APIRouter(prefix="/api/v1", tags=["conversations"])
DatabaseSession = Annotated[Session, Depends(get_db)]
RequestAgent = Annotated[
    CurrentUser,
    Depends(require_roles("RequestAgent", "RequestAdmin")),
]


@router.post(
    "/requests/{request_document_id}/conversation",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
)
async def start_conversation(
    request_document_id: str,
    user: RequestAgent,
    strapi: StrapiDependency,
    db: DatabaseSession,
) -> Conversation:
    request = await strapi.get_request(request_document_id)
    return open_conversation(db, request, user)


async def _accessible_conversation(
    conversation_id: int,
    user: CurrentUser,
    strapi: StrapiDependency,
    db: Session,
):
    conversation = get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    request = await strapi.ensure_request_access(conversation.request_document_id, user)
    return conversation, request


@router.get("/conversations/{conversation_id}/messages", response_model=list[Message])
async def get_messages(
    conversation_id: int,
    user: PortalUser,
    strapi: StrapiDependency,
    db: DatabaseSession,
) -> list[Message]:
    conversation, _ = await _accessible_conversation(conversation_id, user, strapi, db)
    return list_messages(db, conversation.id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    user: PortalUser,
    strapi: StrapiDependency,
    db: DatabaseSession,
) -> Message:
    conversation, request = await _accessible_conversation(conversation_id, user, strapi, db)
    if conversation.closed_at is not None:
        raise HTTPException(status_code=409, detail="Conversation is closed")
    return create_message(db, conversation, request, user, payload.body)