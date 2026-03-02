from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from iota_verbum_api.config import settings
from iota_verbum_api.utils import hash_sensitive


@dataclass(frozen=True)
class AuthContext:
    api_key: str
    api_key_hash: str
    tenant_id: str


def authenticate_api_key(x_api_key: str | None = Header(default=None)) -> AuthContext:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication_failed"},
        )

    tenant_id = settings.api_keys.get(x_api_key)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication_failed"},
        )

    return AuthContext(
        api_key=x_api_key,
        api_key_hash=hash_sensitive(x_api_key),
        tenant_id=tenant_id,
    )

