from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.services.db import Base


class RequestEventRecord(Base):
    __tablename__ = "request_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_document_id: Mapped[str] = mapped_column(String(255), index=True)
    actor_sub: Mapped[str] = mapped_column(String(255), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    previous_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RequestEventPayload(BaseModel):
    event_type: str
    previous_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None


class RequestEventCreate(RequestEventPayload):
    request_document_id: str
    actor_sub: str


class RequestEvent(RequestEventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class RequestReference(BaseModel):
    document_id: str | None = None
    name: str | None = None


class RequestUser(BaseModel):
    subject: str | None = None
    email: str | None = None
    name: str | None = None


class RequestView(BaseModel):
    document_id: str
    request_number: str
    status: str
    requester: RequestUser
    assigned_to: RequestUser | None = None
    service_task: RequestReference
    location: RequestReference | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RequestList(BaseModel):
    items: list[RequestView]
    page: int
    page_size: int
    total: int


