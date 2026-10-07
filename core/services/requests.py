from sqlalchemy import select
from sqlalchemy.orm import Session

from core.domain.requests_model import RequestEventCreate, RequestEventRecord


def create_request_event(db: Session, event: RequestEventCreate) -> RequestEventRecord:
    record = RequestEventRecord(**event.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_request_events(db: Session, request_document_id: str) -> list[RequestEventRecord]:
    statement = (
        select(RequestEventRecord)
        .where(RequestEventRecord.request_document_id == request_document_id)
        .order_by(RequestEventRecord.created_at.desc())
    )
    return list(db.scalars(statement))
