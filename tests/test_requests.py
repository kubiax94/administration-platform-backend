import asyncio

from httpx import ASGITransport, AsyncClient

from core.domain.auth_model import CurrentUser
from core.domain.requests_model import RequestList
from core.services.auth import get_current_user
from core.services.dependencies import get_strapi
from main import fastapi_app


class FakeStrapi:
    received_subject: str | None = None

    async def list_user_requests(self, user: CurrentUser, page: int, page_size: int) -> RequestList:
        self.received_subject = user.subject
        return RequestList(items=[], page=page, page_size=page_size, total=0)


def test_mine_uses_authenticated_subject() -> None:
    fake_strapi = FakeStrapi()
    fastapi_app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        subject="entra-oid",
        email="user@example.com",
        roles=frozenset({"Employee"}),
        scopes=frozenset({"access_as_user"}),
        client_id="frontend-client",
    )
    fastapi_app.dependency_overrides[get_strapi] = lambda: fake_strapi

    async def request_mine():
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/requests/mine?page=2&page_size=10")

    try:
        response = asyncio.run(request_mine())
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 2, "page_size": 10, "total": 0}
    assert fake_strapi.received_subject == "entra-oid"


def test_mine_rejects_user_without_portal_role() -> None:
    fastapi_app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        subject="entra-oid",
        scopes=frozenset({"access_as_user"}),
        client_id="frontend-client",
    )

    async def request_mine():
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/requests/mine")

    try:
        response = asyncio.run(request_mine())
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 403


def test_internal_employee_is_a_portal_user() -> None:
    fake_strapi = FakeStrapi()
    fastapi_app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        subject="entra-oid",
        roles=frozenset({"InternalEmployee"}),
        scopes=frozenset({"access_as_user"}),
        client_id="frontend-client",
    )
    fastapi_app.dependency_overrides[get_strapi] = lambda: fake_strapi

    async def request_mine():
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/requests/mine")

    try:
        response = asyncio.run(request_mine())
    finally:
        fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200