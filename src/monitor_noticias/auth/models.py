from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(
    frozen=True,
    slots=True,
)
class AuthUser:
    username: str
    name: str
    profile: str
    permissions: frozenset[str]
    must_change_password: bool = False

    def can(
        self,
        permission: str,
    ) -> bool:
        return (
            permission
            in self.permissions
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AuthSession:
    token: str
    expires_at: datetime | None
    user: AuthUser

    @property
    def display_name(
        self,
    ) -> str:
        return (
            self.user.name
            or self.user.username
        )
