from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models.sales_leads import (
    LeadSource,
    LeadStatus,
    SalesLeadCreate,
    SalesLeadListItem,
    SalesLeadListResponse,
    SalesLeadRead,
    SalesLeadUpdate,
)
from app.routers._auth import parse_user_id_or_401
from app.services.sales_leads import SalesLeadsService
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix="/customerCenter/salesLeads", tags=["Sales Leads"])
service = SalesLeadsService()


@router.get(
    "",
    response_model=SalesLeadListResponse,
    summary="List sales leads",
    description="List sales leads for the current authenticated user.",
)
async def list_sales_leads(
    keyword: str | None = Query(default=None),
    status_value: LeadStatus | None = Query(default=None, alias="status"),
    lead_source: LeadSource | None = Query(default=None),
    location: str | None = Query(default=None),
    created_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="created_at.desc.nullslast"),
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        total, rows = await service.list_sales_leads(
            owner_user_id=owner_user_id,
            keyword=keyword,
            lead_status=status_value,
            lead_source=lead_source,
            location=location,
            created_date=created_date,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    items: list[SalesLeadListItem] = []
    for row in rows:
        owner = row.get("user_profiles") or {}
        if isinstance(owner, list):
            owner = owner[0] if owner else {}
        owner_name = owner.get("full_name") or owner.get("email")
        item_payload: dict[str, Any] = {
            "id": row.get("id"),
            "owner_user_id": row.get("owner_user_id"),
            "contact_name": row.get("contact_name") or "",
            "contact_email": row.get("contact_email") or "",
            "phone_number": row.get("phone_number"),
            "interested_product": row.get("interested_product"),
            "message": row.get("message"),
            "location": row.get("location"),
            "lead_source": row.get("lead_source") or "Shopify Website",
            "source_campaign": row.get("source_campaign"),
            "lead_status": row.get("lead_status") or "Unfollowed",
            "owner_name": owner_name,
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        items.append(SalesLeadListItem(**item_payload))

    return SalesLeadListResponse(total=total, items=items)


@router.get(
    "/{lead_id}",
    response_model=SalesLeadRead,
    summary="Get sales lead details",
)
async def get_sales_lead(
    lead_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        row = await service.get_sales_lead(lead_id=lead_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead not found")

    return SalesLeadRead(**row)


@router.post(
    "",
    response_model=SalesLeadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create sales lead",
)
async def create_sales_lead(
    payload: SalesLeadCreate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    create_payload = payload.model_dump(exclude_none=True)
    create_payload["owner_user_id"] = owner_user_id

    try:
        row = await service.create_sales_lead(create_payload)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SalesLeadRead(**row)


@router.patch(
    "/{lead_id}",
    response_model=SalesLeadRead,
    summary="Update sales lead",
)
async def update_sales_lead(
    lead_id: str,
    payload: SalesLeadUpdate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> SalesLeadRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    update_payload = payload.model_dump(exclude_none=True)

    if not update_payload:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        row = await service.update_sales_lead(
            lead_id=lead_id,
            owner_user_id=owner_user_id,
            payload=update_payload,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead not found")
    return SalesLeadRead(**row)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete sales lead",
)
async def delete_sales_lead(
    lead_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> None:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        deleted = await service.delete_sales_lead(lead_id=lead_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales lead not found")
