from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.models.store_management import SubordinateAgentListResponse
from app.routers._auth import parse_user_id_or_401
from app.services.store_management import StoreManagementService
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix="/customerCenter/agents", tags=["Subordinate Agents"])
service = StoreManagementService()


@router.get(
    "",
    response_model=SubordinateAgentListResponse,
    summary="List subordinate agents",
    description="Used by customerCenter/agents page.",
)
async def list_subordinate_agents(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SubordinateAgentListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        total, items = await service.list_subordinate_agents(
            owner_user_id=owner_user_id,
            keyword=keyword,
            status=status,
            limit=limit,
            offset=offset,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SubordinateAgentListResponse(total=total, items=items)
