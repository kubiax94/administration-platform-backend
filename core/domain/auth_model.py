from pydantic import BaseModel


class CurrentUser(BaseModel):
    subject: str
    email: str | None = None
    name: str | None = None
    roles: frozenset[str] = frozenset()
    scopes: frozenset[str] = frozenset()
    client_id: str

    def has_any_role(self, roles: set[str]) -> bool:
        return bool(self.roles.intersection(roles))