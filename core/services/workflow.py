from sqlalchemy import select
from sqlalchemy.orm import Session

from core.domain.auth_model import CurrentUser
from core.domain.requests_model import RequestView
from core.domain.workflow_model import (
    ConversationRecord,
    MessageRecord,
    NotificationOutboxRecord,
)


def get_conversation(db: Session, conversation_id: int) -> ConversationRecord | None:
    return db.get(ConversationRecord, conversation_id)


def get_request_conversation(db: Session, request_document_id: str) -> ConversationRecord | None:
    return db.scalar(
        select(ConversationRecord).where(
            ConversationRecord.request_document_id == request_document_id
        )
    )


def open_conversation(
    db: Session,
    request: RequestView,
    user: CurrentUser,
) -> ConversationRecord:
    existing = get_request_conversation(db, request.document_id)
    if existing is not None:
        return existing

    conversation = ConversationRecord(
        request_document_id=request.document_id,
        opened_by_sub=user.subject,
    )
    db.add(conversation)
    if request.requester.email:
        db.add(
            NotificationOutboxRecord(
                request_document_id=request.document_id,
                event_type="conversation_opened",
                recipient=request.requester.email,
                payload={"request_number": request.request_number},
            )
        )
    db.commit()
    db.refresh(conversation)
    return conversation


def list_messages(db: Session, conversation_id: int) -> list[MessageRecord]:
    statement = (
        select(MessageRecord)
        .where(MessageRecord.conversation_id == conversation_id)
        .order_by(MessageRecord.created_at.asc())
    )
    return list(db.scalars(statement))


def create_message(
    db: Session,
    conversation: ConversationRecord,
    request: RequestView,
    user: CurrentUser,
    body: str,
) -> MessageRecord:
    message = MessageRecord(
        conversation_id=conversation.id,
        sender_sub=user.subject,
        body=body,
    )
    db.add(message)

    privileged = user.has_any_role({"RequestAgent", "RequestAdmin"})
    recipient = request.requester.email if privileged else (
        request.assigned_to.email if request.assigned_to else None
    )
    if recipient:
        db.add(
            NotificationOutboxRecord(
                request_document_id=request.document_id,
                event_type="new_chat_message",
                recipient=recipient,
                payload={"conversation_id": conversation.id},
            )
        )
    db.commit()
    db.refresh(message)
    return message