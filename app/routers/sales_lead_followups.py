from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models.sales_lead_followups import (
    SalesLeadFollowupCreate,
    SalesLeadFollowupListResponse,
    SalesLeadFollowupRead,
)
from app.routers._auth import parse_user_id_or_401
from app.services.sales_lead_followups import SalesLeadFollowupsService
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(
    prefix="/customerCenter/salesLeads/{lead_id}/followups",
    tags=["Sales Lead Follow-ups"],
)
service = SalesLeadFollowupsService()


async def _ensure_lead_exists(*, lead_id: UUID, owner_user_id: str) -> None:
    exists = await service.lead_exists_for_owner(lead_id=str(lead_id), owner_user_id=owner_user_id)
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead not found")


@router.get(
    "",
    response_model=SalesLeadFollowupListResponse,
    summary="List lead follow-ups",
)
async def list_followups(
    lead_id: UUID,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="created_at.desc.nullslast"),
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadFollowupListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        await _ensure_lead_exists(lead_id=lead_id, owner_user_id=owner_user_id)
        total, rows = await service.list_followups(
            owner_user_id=owner_user_id,
            lead_id=str(lead_id),
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SalesLeadFollowupListResponse(
        total=total,
        items=[SalesLeadFollowupRead(**row) for row in rows],
    )


@router.get(
    "/{followup_id}",
    response_model=SalesLeadFollowupRead,
    summary="Get lead follow-up details",
)
async def get_followup(
    lead_id: UUID,
    followup_id: UUID,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadFollowupRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        await _ensure_lead_exists(lead_id=lead_id, owner_user_id=owner_user_id)
        row = await service.get_followup(
            followup_id=str(followup_id),
            lead_id=str(lead_id),
            owner_user_id=owner_user_id,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead follow-up not found")
    return SalesLeadFollowupRead(**row)


@router.post(
    "",
    response_model=SalesLeadFollowupRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead follow-up",
)
async def create_followup(
    lead_id: UUID,
    payload: SalesLeadFollowupCreate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadFollowupRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    create_payload = payload.model_dump(exclude_none=True)
    create_payload["sales_lead_id"] = str(lead_id)
    create_payload["owner_user_id"] = owner_user_id

    try:
        await _ensure_lead_exists(lead_id=lead_id, owner_user_id=owner_user_id)
        row = await service.create_followup(create_payload)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SalesLeadFollowupRead(**row)


@router.delete(
    "/{followup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead follow-up",
)
async def delete_followup(
    lead_id: UUID,
    followup_id: UUID,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> None:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        await _ensure_lead_exists(lead_id=lead_id, owner_user_id=owner_user_id)
        deleted = await service.delete_followup(
            followup_id=str(followup_id),
            lead_id=str(lead_id),
            owner_user_id=owner_user_id,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead follow-up not found")
