from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.services.db import Base


class ConversationRecord(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("request_document_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_document_id: Mapped[str] = mapped_column(String(255), index=True)
    opened_by_sub: Mapped[str] = mapped_column(String(255), index=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    messages: Mapped[list["MessageRecord"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    sender_sub: Mapped[str] = mapped_column(String(255), index=True)
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    conversation: Mapped[ConversationRecord] = relationship(back_populates="messages")


class NotificationOutboxRecord(Base):
    __tablename__ = "notification_outbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_document_id: Mapped[str] = mapped_column(String(255), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    recipient: Mapped[str] = mapped_column(String(320), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    delivery_status: Mapped[str] = mapped_column(
        String(32), server_default="pending", index=True
    )
    attempts: Mapped[int] = mapped_column(server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_document_id: str
    opened_by_sub: str
    opened_at: datetime
    closed_at: datetime | None


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_sub: str
    body: str
    read_at: datetime | None
    created_at: datetime