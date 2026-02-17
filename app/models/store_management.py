from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


StoreStatus = Literal["active", "pending", "inactive"]
StoreCreateType = Literal["independent", "chain"]


class StoreManagementListItem(BaseModel):
    store_id: UUID
    store_name: str
    authorization_code: str | None = None

    agent_id: UUID | None = None
    agent_company_name: str | None = None
    proxy_account: str | None = None

    client_count: int = 0
    company_location: str | None = None
    sales_area: str | None = None
    store_count: int = 0
    binding_count: int = 0
    superior_agent_name: str | None = None

    created_at: datetime | None = None
    status: StoreStatus = "active"


class StoreManagementListResponse(BaseModel):
    total: int
    items: list[StoreManagementListItem]


class StoreMerchantInfo(BaseModel):
    merchant_name: str | None = None
    administrator_account: str | None = None
    administrator_email: str | None = None


class StoreShopInfo(BaseModel):
    store_id: UUID
    store_name: str
    authorization_code: str | None = None
    store_address: str | None = None
    industry_sector: str | None = None
    store_contact: str | None = None
    contact_position: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    platform_source_address: str | None = None
    agent_id: UUID | None = None
    agent_name: str | None = None
    agent_email: str | None = None


class StoreWaitstaffInfo(BaseModel):
    display_name: str
    email: str | None = None


class StoreManagementDetailResponse(BaseModel):
    merchant_info: StoreMerchantInfo
    shop_info: StoreShopInfo
    waitstaff: list[StoreWaitstaffInfo] = Field(default_factory=list)


class StoreManagementAccountItem(BaseModel):
    account: str
    role: str | None = None
    email: str | None = None
    status: str | None = None


class StoreManagementAccountListResponse(BaseModel):
    total: int
    items: list[StoreManagementAccountItem]


class StoreAgentOption(BaseModel):
    id: UUID
    name: str
    email: str | None = None


class StoreAgentOptionListResponse(BaseModel):
    total: int
    items: list[StoreAgentOption]


class StoreManagementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    create_type: StoreCreateType = "independent"
    store_name: str = Field(..., min_length=1, max_length=150)
    authorization_code: str | None = Field(default=None, max_length=100)

    agent_id: UUID | None = None
    agent_name: str | None = Field(default=None, max_length=150)

    industry_sector: str | None = None
    store_address: str | None = None
    store_contact: str | None = None
    contact_position: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    merchant_name: str | None = None


class StoreManagementUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_name: str | None = Field(default=None, min_length=1, max_length=150)
    authorization_code: str | None = Field(default=None, max_length=100)
    agent_id: UUID | None = None


class StoreManagementCreateResponse(BaseModel):
    store_id: UUID
    store_name: str
    authorization_code: str | None = None
    agent_id: UUID | None = None
    created_at: datetime | None = None


class StoreManagementQuery(BaseModel):
    keyword: str | None = Field(default=None, description="Store name/code fuzzy keyword")
    agent_name_or_account: str | None = None
    client_count: int | None = Field(default=None, ge=0)
    company_location: str | None = None
    status: StoreStatus | None = None
    sales_area: str | None = None
    created_date: str | None = Field(default=None, description="YYYY-MM-DD")
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    order_by: str = Field(default="created_at.desc.nullslast")
