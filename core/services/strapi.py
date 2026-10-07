from typing import Any

import httpx
from fastapi import HTTPException, status

from core.domain.auth_model import CurrentUser
from core.domain.requests_model import RequestList, RequestReference, RequestUser, RequestView
from core.settings import Settings


def _record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    attributes = value.get("attributes")
    return {**value, **attributes} if isinstance(attributes, dict) else value


def _entities(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and "data" in value:
        value = value["data"]
    if isinstance(value, list):
        return [_record(item) for item in value]
    return [_record(value)] if isinstance(value, dict) else []


def _relation(value: Any) -> dict[str, Any]:
    entities = _entities(value)
    return entities[0] if entities else {}


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _document_id(value: dict[str, Any]) -> str | None:
    identifier = value.get("documentId") or value.get("id")
    return str(identifier) if identifier is not None else None


def _map_user(value: Any) -> RequestUser:
    user = _relation(value)
    name_parts = [user.get("firstname"), user.get("lastname")]
    name = " ".join(part for part in name_parts if isinstance(part, str)) or _string(user.get("username"))
    return RequestUser(
        subject=_string(user.get("subid")) or _string(user.get("oid")),
        email=_string(user.get("email")),
        name=name,
    )


def _map_request(item: dict[str, Any]) -> RequestView:
    service_task = _relation(item.get("service_task"))
    location = _relation(item.get("main_location"))
    assigned_to = _relation(item.get("assigned_to"))
    document_id = _document_id(item)
    if document_id is None:
        raise ValueError("Strapi request does not contain documentId or id")

    return RequestView(
        document_id=document_id,
        request_number=_string(item.get("id_request")) or document_id,
        status=_string(item.get("req_status")) or "Utworzony",
        requester=_map_user(item.get("requested_by")),
        assigned_to=_map_user(assigned_to) if assigned_to else None,
        service_task=RequestReference(
            document_id=_document_id(service_task),
            name=_string(service_task.get("name")),
        ),
        location=RequestReference(
            document_id=_document_id(location),
            name=_string(location.get("name")),
        ) if location else None,
        created_at=item.get("createdAt"),
        updated_at=item.get("updatedAt"),
    )


class StrapiService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if not self.settings.strapi_url:
            return
        headers = {"Accept": "application/json"}
        if self.settings.strapi_key:
            headers["Authorization"] = f"Bearer {self.settings.strapi_key}"
        self.client = httpx.AsyncClient(
            base_url=self.settings.strapi_url.rstrip("/"),
            headers=headers,
            timeout=15,
        )

    async def stop(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Strapi integration is not configured",
            )
        try:
            response = await self.client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {"data": payload}
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Request not found") from error
            raise HTTPException(status_code=502, detail="Strapi rejected the request") from error
        except (httpx.HTTPError, ValueError) as error:
            raise HTTPException(status_code=502, detail="Strapi is unavailable") from error

    @staticmethod
    def _populate_params() -> dict[str, str]:
        return {
            "populate[requested_by]": "true",
            "populate[service_task]": "true",
            "populate[main_location]": "true",
        }

    async def list_user_requests(self, user: CurrentUser, page: int, page_size: int) -> RequestList:
        params: dict[str, Any] = {
            **self._populate_params(),
            "filters[requested_by][subid][$eq]": user.subject,
            "pagination[page]": page,
            "pagination[pageSize]": page_size,
            "sort": "createdAt:desc",
        }
        payload = await self._get("/api/requests", params)
        items = [_map_request(item) for item in _entities(payload)]
        pagination = _record(_record(payload.get("meta")).get("pagination"))
        return RequestList(
            items=items,
            page=int(pagination.get("page", page)),
            page_size=int(pagination.get("pageSize", page_size)),
            total=int(pagination.get("total", len(items))),
        )

    async def get_request(self, document_id: str) -> RequestView:
        payload = await self._get(f"/api/requests/{document_id}", self._populate_params())
        items = _entities(payload)
        if not items:
            raise HTTPException(status_code=404, detail="Request not found")
        return _map_request(items[0])

    async def ensure_request_access(self, document_id: str, user: CurrentUser) -> RequestView:
        request = await self.get_request(document_id)
        privileged_roles = {"RequestAgent", "RequestAdmin"}
        if request.requester.subject != user.subject and not user.has_any_role(privileged_roles):
            raise HTTPException(status_code=403, detail="Access to this request is forbidden")
        return request