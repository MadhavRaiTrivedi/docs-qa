import secrets
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from docs_qa.auth.role import Role
from docs_qa.dependencies import get_app_settings
from docs_qa.http_headers import HeaderNames
from docs_qa.settings import Settings


class MissingApiKeyError(Exception):
    def __init__(self) -> None:
        super().__init__(f"Send a valid API key in the {HeaderNames.API_KEY} header.")


class InsufficientRoleError(Exception):
    def __init__(self, required: Role) -> None:
        super().__init__(f"This action needs the {required} role.")


_GRANTED_ROLES = {
    Role.READER: frozenset({Role.READER}),
    Role.EDITOR: frozenset({Role.READER, Role.EDITOR}),
}

_api_key_header = APIKeyHeader(name=HeaderNames.API_KEY, auto_error=False)


def role_for_key(api_key: str | None, settings: Settings) -> Role:
    if api_key:
        # Compare against every key in constant time, so response timing reveals nothing.
        matches = [
            role
            for known_key, role in settings.auth.api_keys.items()
            if secrets.compare_digest(known_key.encode(), api_key.encode())
        ]
        if matches:
            return matches[0]
    raise MissingApiKeyError()


async def current_role(
    api_key: Annotated[str | None, Security(_api_key_header)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Role:
    return role_for_key(api_key, settings)


def require_role(required: Role) -> Callable[..., Awaitable[Role]]:
    async def check(role: Annotated[Role, Depends(current_role)]) -> Role:
        if required not in _GRANTED_ROLES[role]:
            raise InsufficientRoleError(required)
        return role

    return check


RequireReader = Depends(require_role(Role.READER))
RequireEditor = Depends(require_role(Role.EDITOR))
