from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from core.domain.auth_model import CurrentUser
from core.domain.requests_model import RequestReference, RequestUser, RequestView
from core.domain.workflow_model import NotificationOutboxRecord
from core.services.db import Base
from core.services.workflow import create_message, list_messages, open_conversation


def test_conversation_message_and_notification_outbox() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    request = RequestView(
        document_id="request-doc",
        request_number="REQ-1",
        status="Utworzony",
        requester=RequestUser(subject="requester", email="requester@example.com"),
        assigned_to=RequestUser(subject="agent", email="agent@example.com"),
        service_task=RequestReference(document_id="task-doc", name="Dostępy"),
    )
    admin = CurrentUser(
        subject="agent",
        roles=frozenset({"RequestAgent"}),
        scopes=frozenset({"access_as_user"}),
        client_id="frontend-client",
    )

    with Session(engine) as db:
        conversation = open_conversation(db, request, admin)
        message = create_message(db, conversation, request, admin, "Dzień dobry")
        notifications = db.scalar(select(func.count()).select_from(NotificationOutboxRecord))

        assert message.sender_sub == "agent"
        assert len(list_messages(db, conversation.id)) == 1
        assert notifications == 2