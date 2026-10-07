from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.domain.auth_model import CurrentUser
from core.domain.requests_model import (
	RequestEvent,
	RequestEventCreate,
	RequestEventPayload,
	RequestList,
	RequestView,
)
from core.services.auth import PortalUser, require_roles
from core.services.db import get_db
from core.services.dependencies import StrapiDependency
from core.services.requests import create_request_event, list_request_events


router = APIRouter(prefix="/api/v1/requests", tags=["requests"])
DatabaseSession = Annotated[Session, Depends(get_db)]
RequestAgent = Annotated[
	CurrentUser,
	Depends(require_roles("RequestAgent", "RequestAdmin")),
]


@router.get("/mine", response_model=RequestList)
async def get_my_requests(
	user: PortalUser,
	strapi: StrapiDependency,
	page: Annotated[int, Query(ge=1)] = 1,
	page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> RequestList:
	return await strapi.list_user_requests(user, page, page_size)


@router.get("/{request_document_id}", response_model=RequestView)
async def get_request(
	request_document_id: str,
	user: PortalUser,
	strapi: StrapiDependency,
) -> RequestView:
	return await strapi.ensure_request_access(request_document_id, user)


@router.get("/{request_document_id}/events", response_model=list[RequestEvent])
async def get_events(
	request_document_id: str,
	user: PortalUser,
	strapi: StrapiDependency,
	db: DatabaseSession,
) -> list[RequestEvent]:
	await strapi.ensure_request_access(request_document_id, user)
	return list_request_events(db, request_document_id)


@router.post(
	"/{request_document_id}/events",
	response_model=RequestEvent,
	status_code=status.HTTP_201_CREATED,
)
async def create_event(
	request_document_id: str,
	payload: RequestEventPayload,
	user: RequestAgent,
	strapi: StrapiDependency,
	db: DatabaseSession,
) -> RequestEvent:
	await strapi.get_request(request_document_id)
	event = RequestEventCreate(
		**payload.model_dump(),
		request_document_id=request_document_id,
		actor_sub=user.subject,
	)
	return create_request_event(db, event)
