from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


StoreScope = Literal["all", "installed", "unbound"]


class MachineProductLibraryBase(BaseModel):
    product_name: str | None = None
    product_nickname: str | None = None
    sn_pid: str = Field(..., description="Machine serial number (SN/PID)")
    mac_address: str | None = None
    store_id: UUID | None = None
    agent_id: UUID | None = None
    use_type: str | None = Field(default=None, description="Purchase/Lease/Trial")
    remaining_warranty_days: Decimal | None = None
    status: str
    store_installation_time: datetime | None = None
    first_active_time: datetime | None = None
    software_version: str | None = None
    firmware_version: str | None = None
    last_seen_at: datetime | None = None
    last_ip: str | None = None
    model_id: UUID | None = None
    group_id: UUID | None = None
    site_use: str | None = None
    warranty_months: int | None = None
    activated_at: datetime | None = None
    last_boot_at: datetime | None = None
    status_updated_at: datetime | None = None
    frozen_at: datetime | None = None
    expires_at: datetime | None = None
    import_time: datetime | None = None


class MachineProductLibraryCreate(MachineProductLibraryBase):
    pass


class MachineProductLibraryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_nickname: str | None = None
    use_type: str | None = None
    site_use: str | None = None
    group_id: UUID | None = None
    warranty_months: int | None = None


class MachineProductLibraryQuery(BaseModel):
    model_or_product_name: str | None = Field(
        default=None,
        description="Filters product_name or product_nickname by partial match",
    )
    sn_pid: str | None = None
    status: str | None = None
    agent_id: UUID | None = None
    software_version: str | None = None
    firmware_version: str | None = None
    store_scope: StoreScope = "all"
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="import_time.desc.nullslast")


class MachineProductLibraryRead(MachineProductLibraryBase):
    model_config = ConfigDict(extra="allow")

    id: UUID
    created_at: datetime
    updated_at: datetime


class MachineProductLibraryListResponse(BaseModel):
    total: int
    items: list[MachineProductLibraryRead]
