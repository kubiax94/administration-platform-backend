from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_connect: str = "localhost"
    db_port: int = 5433
    db_user: str
    db_password: str
    db_name: str
    strapi_key: str = ""
    strapi_url: str = ""
    azure_tenant_id: str = ""
    azure_audience: str = ""
    azure_required_scope: str = "access_as_user"
    azure_allowed_client_ids: str = ""
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def allowed_client_ids(self) -> frozenset[str]:
        return frozenset(
            client_id.strip()
            for client_id in self.azure_allowed_client_ids.split(",")
            if client_id.strip()
        )

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]