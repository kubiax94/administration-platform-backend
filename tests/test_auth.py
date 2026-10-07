from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from core.services.auth import EntraTokenValidator


class SigningKey:
    def __init__(self, key):
        self.key = key


class StaticJwksClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token: str):
        return SigningKey(self.key)


def create_token(private_key, tenant_id: str, audience: str, **claims):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "oid": "user-oid",
            "tid": tenant_id,
            "iss": f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "scp": "access_as_user",
            "azp": "frontend-client",
            "roles": ["RequestAdmin"],
            **claims,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def create_validator(private_key, tenant_id: str, audience: str) -> EntraTokenValidator:
    validator = EntraTokenValidator(
        tenant_id,
        audience,
        "access_as_user",
        frozenset({"frontend-client"}),
    )
    validator.jwks_client = StaticJwksClient(private_key.public_key())
    return validator


def test_entra_token_signature_issuer_audience_scope_and_client() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tenant_id = "test-tenant"
    audience = "api://administration-platform"
    token = create_token(private_key, tenant_id, audience)
    validator = create_validator(private_key, tenant_id, audience)

    claims = validator.decode(token)

    assert claims["oid"] == "user-oid"
    assert claims["roles"] == ["RequestAdmin"]


def test_entra_v1_token_with_api_audience() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tenant_id = "test-tenant"
    application_id = "backend-client-id"
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "oid": "user-oid",
            "tid": tenant_id,
            "iss": f"https://sts.windows.net/{tenant_id}/",
            "aud": f"api://{application_id}",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "scp": "access_as_user",
            "appid": "frontend-client",
            "roles": ["InternalEmployee"],
            "upn": "user@example.com",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    validator = create_validator(private_key, tenant_id, application_id)

    claims = validator.decode(token)

    assert claims["aud"] == f"api://{application_id}"
    assert claims["roles"] == ["InternalEmployee"]


@pytest.mark.parametrize(
    "claims",
    [
        {"scp": "other_scope"},
        {"azp": "untrusted-client"},
    ],
)
def test_entra_token_rejects_wrong_scope_or_client(claims: dict[str, str]) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tenant_id = "test-tenant"
    audience = "api://administration-platform"
    validator = create_validator(private_key, tenant_id, audience)
    token = create_token(private_key, tenant_id, audience, **claims)

    with pytest.raises(jwt.InvalidTokenError):
        validator.decode(token)