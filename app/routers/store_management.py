from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models.store_management import (
    StoreStatus,
    StoreAgentOptionListResponse,
    StoreManagementAccountListResponse,
    StoreManagementCreate,
    StoreManagementCreateResponse,
    StoreManagementDetailResponse,
    StoreManagementListItem,
    StoreManagementListResponse,
    StoreManagementUpdate,
    StoreMerchantInfo,
    StoreShopInfo,
)
from app.routers._auth import parse_user_id_or_401
from app.services.store_management import StoreManagementService
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix="/customerCenter/storeManagement", tags=["Store Management"])
service = StoreManagementService()


@router.get(
    "",
    response_model=StoreManagementListResponse,
    summary="List store management cards",
    description=(
        "List stores with related agent info and metrics used by "
        "customerCenter/storeManagement page filters/table."
    ),
)
async def list_store_management_rows(
    keyword: str | None = Query(default=None),
    agent_name_or_account: str | None = Query(default=None),
    client_count: int | None = Query(default=None, ge=0),
    company_location: str | None = Query(default=None),
    status_value: StoreStatus | None = Query(default=None, alias="status"),
    sales_area: str | None = Query(default=None),
    created_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    creation_time: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="created_at.desc.nullslast"),
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> StoreManagementListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    resolved_created_date = created_date or creation_time

    try:
        _, rows = await service.list_store_cards(
            owner_user_id=owner_user_id,
            keyword=keyword,
            agent_name_or_account=agent_name_or_account,
            created_date=resolved_created_date,
            limit=10_000,
            offset=0,
            order_by=order_by,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not rows:
        return StoreManagementListResponse(total=0, items=[])

    agent_ids = sorted({str(item.get("agent_id")) for item in rows if item.get("agent_id")})
    try:
        metrics = await service.build_agent_metrics(agent_ids, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    filtered_items: list[StoreManagementListItem] = []
    for row in rows:
        agent = row.get("agents") or {}
        agent_id = str(row.get("agent_id")) if row.get("agent_id") else None
        row_metrics = metrics.get(agent_id or "", {"store_count": 0, "binding_count": 0, "client_count": 0})
        row_status = service.derive_status(
            binding_count=row_metrics["binding_count"],
            authorization_code=row.get("code"),
            store_name=row.get("name"),
        )

        if status_value and row_status != status_value:
            continue
        if client_count is not None and row_metrics["client_count"] != client_count:
            continue
        row_company_location = row.get("company_location") or agent.get("company_location")
        if company_location:
            location_keyword = company_location.strip().lower()
            location_value = str(row_company_location or "").lower()
            if location_keyword not in location_value:
                continue
        row_sales_area = row.get("sales_area") or agent.get("sales_area")
        if sales_area:
            if str(row_sales_area or "").lower() != sales_area.strip().lower():
                continue

        filtered_items.append(
            StoreManagementListItem(
                store_id=row["id"],
                store_name=row.get("name") or "",
                authorization_code=row.get("code"),
                agent_id=row.get("agent_id"),
                agent_company_name=agent.get("name"),
                proxy_account=agent.get("email"),
                client_count=row_metrics["client_count"],
                company_location=row_company_location,
                sales_area=row_sales_area,
                store_count=row_metrics["store_count"],
                binding_count=row_metrics["binding_count"],
                superior_agent_name=None,
                created_at=row.get("created_at") or agent.get("created_at"),
                status=row_status,
            )
        )

    total_value = len(filtered_items)
    paged_items = filtered_items[offset : offset + limit]
    return StoreManagementListResponse(total=total_value, items=paged_items)


@router.get(
    "/agents/options",
    response_model=StoreAgentOptionListResponse,
    summary="List agent options for store forms",
)
async def list_store_agent_options(
    keyword: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> StoreAgentOptionListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        items = await service.list_agent_options(
            owner_user_id=owner_user_id,
            keyword=keyword,
            limit=limit,
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StoreAgentOptionListResponse(total=len(items), items=items)


@router.get(
    "/{store_id}",
    response_model=StoreManagementDetailResponse,
    summary="Get store details",
    description="Used by customerCenter/storeManagement/view page.",
)
async def get_store_detail(
    store_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> StoreManagementDetailResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        row = await service.get_store_by_id(store_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    agent = row.get("agents") or {}

    return StoreManagementDetailResponse(
        merchant_info=StoreMerchantInfo(
            merchant_name=None,
            administrator_account=None,
            administrator_email=None,
        ),
        shop_info=StoreShopInfo(
            store_id=row["id"],
            store_name=row.get("name") or "",
            authorization_code=row.get("code"),
            store_address=None,
            industry_sector=None,
            store_contact=None,
            contact_position=None,
            contact_phone=None,
            contact_email=None,
            platform_source_address=None,
            agent_id=row.get("agent_id"),
            agent_name=agent.get("name"),
            agent_email=agent.get("email"),
        ),
        waitstaff=[],
    )


@router.get(
    "/{store_id}/accounts",
    response_model=StoreManagementAccountListResponse,
    summary="List store accounts",
    description="Used by customerCenter/storeManagement/view account tab.",
)
async def list_store_accounts(
    store_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> StoreManagementAccountListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        row = await service.get_store_by_id(store_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    # The current schema has no dedicated store account table yet.
    return StoreManagementAccountListResponse(total=0, items=[])


@router.post(
    "",
    response_model=StoreManagementCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a store",
    description="Used by customerCenter/storeManagement/add page save action.",
)
async def create_store(
    payload: StoreManagementCreate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> StoreManagementCreateResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        resolved_agent_id = await service.ensure_agent(
            owner_user_id=owner_user_id,
            agent_id=service.parse_uuid(payload.agent_id),
            agent_name=payload.agent_name,
        )

        create_payload: dict[str, Any] = {
            "name": payload.store_name,
            "code": payload.authorization_code or service.generate_store_code(),
            "owner_user_id": owner_user_id,
        }
        if resolved_agent_id:
            create_payload["agent_id"] = resolved_agent_id

        row = await service.create_store(create_payload)
        return StoreManagementCreateResponse(
            store_id=row["id"],
            store_name=row.get("name") or payload.store_name,
            authorization_code=row.get("code"),
            agent_id=row.get("agent_id"),
            created_at=row.get("created_at"),
        )
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.patch(
    "/{store_id}",
    response_model=StoreManagementCreateResponse,
    summary="Update store basic fields",
)
async def update_store(
    store_id: str,
    payload: StoreManagementUpdate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> StoreManagementCreateResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    update_data = payload.model_dump(exclude_none=True)
    if "agent_id" in update_data:
        update_data["agent_id"] = service.parse_uuid(update_data["agent_id"])
    if "store_name" in update_data:
        update_data["name"] = update_data.pop("store_name")
    if "authorization_code" in update_data:
        update_data["code"] = update_data.pop("authorization_code")

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        row = await service.update_store(store_id, owner_user_id=owner_user_id, payload=update_data)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    return StoreManagementCreateResponse(
        store_id=row["id"],
        store_name=row.get("name") or "",
        authorization_code=row.get("code"),
        agent_id=row.get("agent_id"),
        created_at=row.get("created_at"),
    )


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete store",
)
async def delete_store(
    store_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> None:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        deleted = await service.delete_store(store_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
