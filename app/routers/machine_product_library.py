from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.models.machine_product_library import (
    MachineProductLibraryCreate,
    MachineProductLibraryListResponse,
    MachineProductLibraryRead,
    MachineProductLibraryUpdate,
    StoreScope,
)
from app.routers._auth import parse_user_id_or_401
from app.services.supabase_rest import SupabaseRestClient, SupabaseRestError

router = APIRouter(
    prefix="/productCenter/machineProductLibrary",
    tags=["Machine Product Library"],
)
client = SupabaseRestClient()


@router.get(
    "",
    response_model=MachineProductLibraryListResponse,
    summary="List machine products",
    description="Query machine product library records with filters from product list page.",
)
async def list_machine_products(
    model_or_product_name: str | None = Query(default=None),
    sn_pid: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    agent_id: str | None = Query(default=None),
    software_version: str | None = Query(default=None),
    firmware_version: str | None = Query(default=None),
    store_scope: StoreScope = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="import_time.desc.nullslast"),
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> MachineProductLibraryListResponse:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    params: dict[str, str | int] = {
        "select": "*",
        "limit": limit,
        "offset": offset,
        "order": order_by,
    }

    if model_or_product_name:
        keyword = model_or_product_name.replace(",", "").replace("(", "").replace(")", "")
        params["or"] = (
            f"(product_name.ilike.*{keyword}*,product_nickname.ilike.*{keyword}*)"
        )
    if sn_pid:
        params["sn_pid"] = f"eq.{sn_pid}"
    if status_value:
        params["status"] = f"eq.{status_value}"
    if agent_id:
        params["agent_id"] = f"eq.{agent_id}"
    if software_version:
        params["software_version"] = f"eq.{software_version}"
    if firmware_version:
        params["firmware_version"] = f"eq.{firmware_version}"

    if store_scope == "installed":
        params["store_id"] = "not.is.null"
    elif store_scope == "unbound":
        params["store_id"] = "is.null"

    try:
        total, items = await client.list_rows(params=params, owner_user_id=owner_user_id)
        return MachineProductLibraryListResponse(total=total, items=items)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get(
    "/{row_id}",
    response_model=MachineProductLibraryRead,
    summary="Get machine product by ID",
)
async def get_machine_product(
    row_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> MachineProductLibraryRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        row = await client.get_by_id(row_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return MachineProductLibraryRead(**row)


@router.get(
    "/by-sn/{sn_pid}",
    response_model=MachineProductLibraryRead,
    summary="Get machine product by SN(PID)",
)
async def get_machine_product_by_sn(
    sn_pid: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> MachineProductLibraryRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        row = await client.get_by_sn(sn_pid, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return MachineProductLibraryRead(**row)


@router.post(
    "",
    response_model=MachineProductLibraryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create machine product",
)
async def create_machine_product(
    payload: MachineProductLibraryCreate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> MachineProductLibraryRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        create_payload = payload.model_dump(exclude_none=True)
        create_payload["owner_user_id"] = owner_user_id
        row = await client.create_row(create_payload)
        return MachineProductLibraryRead(**row)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.patch(
    "/{row_id}",
    response_model=MachineProductLibraryRead,
    summary="Update editable machine product fields",
    description=(
        "Updates fields aligned with product-edit page: product_nickname, site_use, "
        "group_id, warranty_months, use_type."
    ),
)
async def update_machine_product(
    row_id: str,
    payload: MachineProductLibraryUpdate,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> MachineProductLibraryRead:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        row = await client.update_row(row_id, update_data, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return MachineProductLibraryRead(**row)


@router.delete(
    "/{row_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete machine product",
)
async def delete_machine_product(
    row_id: str,
    x_robotx_user_id: str | None = Header(default=None, alias="x-robotx-user-id"),
) -> None:
    owner_user_id = parse_user_id_or_401(x_robotx_user_id)
    try:
        deleted = await client.delete_row(row_id, owner_user_id=owner_user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
