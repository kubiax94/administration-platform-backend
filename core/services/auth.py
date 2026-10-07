from collections.abc import Callable
from functools import lru_cache
import logging
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import ValidationError

from core.domain.auth_model import CurrentUser
from core.settings import get_settings


bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def _unauthorized(detail: str = "Invalid or missing access token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


class EntraTokenValidator:
    def __init__(
        self,
        tenant_id: str,
        audience: str,
        required_scope: str,
        allowed_client_ids: frozenset[str],
    ) -> None:
        self.tenant_id = tenant_id
        self.audience = audience
        self.required_scope = required_scope
        self.allowed_client_ids = allowed_client_ids
        application_id = audience.removeprefix("api://")
        self.allowed_audiences = {application_id, f"api://{application_id}"}
        self.allowed_issuers = {
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            f"https://sts.windows.net/{tenant_id}/",
        }
        self.jwks_client = PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            cache_keys=True,
        )

    def decode(self, token: str) -> dict[str, Any]:
        signing_key = self.jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=list(self.allowed_audiences),
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
        if claims.get("iss") not in self.allowed_issuers:
            raise jwt.InvalidIssuerError("Token issuer does not match configured tenant")
        if claims.get("tid") != self.tenant_id:
            raise jwt.InvalidTokenError("Token tenant does not match configured tenant")

        scopes_claim = claims.get("scp")
        scopes = set(scopes_claim.split()) if isinstance(scopes_claim, str) else set()
        if self.required_scope and self.required_scope not in scopes:
            raise jwt.InvalidTokenError("Required delegated scope is missing")

        client_id = claims.get("azp") or claims.get("appid")
        if not isinstance(client_id, str) or not client_id:
            raise jwt.InvalidTokenError("Authorized party claim is missing")
        if self.allowed_client_ids and client_id not in self.allowed_client_ids:
            raise jwt.InvalidTokenError("Calling client application is not allowed")
        return claims


@lru_cache
def get_token_validator(
    tenant_id: str,
    audience: str,
    required_scope: str,
    allowed_client_ids: frozenset[str],
) -> EntraTokenValidator:
    return EntraTokenValidator(
        tenant_id,
        audience,
        required_scope,
        allowed_client_ids,
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized()

    settings = get_settings()
    if (
        not settings.azure_tenant_id
        or not settings.azure_audience
        or not settings.allowed_client_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Entra authentication is not configured",
        )

    try:
        claims = get_token_validator(
            settings.azure_tenant_id,
            settings.azure_audience,
            settings.azure_required_scope,
            settings.allowed_client_ids,
        ).decode(credentials.credentials)
        subject = claims.get("oid")
        if not isinstance(subject, str) or not subject:
            raise _unauthorized("Token does not contain a user object identifier")
        roles_claim = claims.get("roles")
        roles = frozenset(role for role in roles_claim if isinstance(role, str)) if isinstance(roles_claim, list) else frozenset()
        scopes_claim = claims.get("scp")
        scopes = frozenset(scopes_claim.split()) if isinstance(scopes_claim, str) else frozenset()
        client_id = claims.get("azp") or claims.get("appid")
        return CurrentUser(
            subject=subject,
            email=(
                claims.get("preferred_username")
                or claims.get("email")
                or claims.get("upn")
                or claims.get("unique_name")
            ),
            name=claims.get("name"),
            roles=roles,
            scopes=scopes,
            client_id=client_id,
        )
    except HTTPException:
        raise
    except (jwt.PyJWTError, ValidationError, ValueError) as error:
        logger.warning("Access token validation failed: %s", error)
        raise _unauthorized("Access token validation failed") from error


AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*allowed_roles: str) -> Callable[[CurrentUser], CurrentUser]:
    allowed = set(allowed_roles)

    def dependency(user: AuthenticatedUser) -> CurrentUser:
        if not user.has_any_role(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency


PortalUser = Annotated[
    CurrentUser,
    Depends(require_roles("Employee", "InternalEmployee", "RequestAgent", "RequestAdmin")),
]