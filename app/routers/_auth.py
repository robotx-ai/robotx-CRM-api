from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status


def parse_user_id_or_401(x_robotx_user_id: str | None) -> str:
    if not x_robotx_user_id or not x_robotx_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-robotx-user-id header",
        )

    raw_user_id = x_robotx_user_id.strip()
    try:
        return str(UUID(raw_user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid x-robotx-user-id header",
        ) from exc
