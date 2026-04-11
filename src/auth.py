"""
Authentication helpers for protecting sensitive DevTrack routes.
"""

from fastapi import Depends, Header, HTTPException, status

from src.config import Settings, get_settings


def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Enforce API key auth when DEVTRACK_API_KEY is configured.

    Accepts either:
    - Authorization: Bearer <key>
    - X-API-Key: <key>
    """
    if not settings.api_key_auth_enabled:
        return

    bearer_key = None
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            bearer_key = token

    provided_key = bearer_key or x_api_key
    if provided_key == settings.devtrack_api_key:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key.",
    )
