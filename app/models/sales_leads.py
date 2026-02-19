from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


LeadStatus = Literal["Unfollowed", "Following Up", "Converted", "Lost"]
LeadSource = Literal["Sales Email", "Shopify Website"]


class SalesLeadListItem(BaseModel):
    id: UUID
    owner_user_id: UUID
    contact_name: str
    contact_email: str
    phone_number: str | None = None
    interested_product: str | None = None
    message: str | None = None
    location: str | None = None
    lead_source: LeadSource
    source_campaign: str | None = None
    lead_status: LeadStatus
    owner_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SalesLeadListResponse(BaseModel):
    total: int
    items: list[SalesLeadListItem]


class SalesLeadRead(BaseModel):
    id: UUID
    owner_user_id: UUID
    contact_name: str
    contact_email: str
    phone_number: str | None = None
    interested_product: str | None = None
    message: str | None = None
    location: str | None = None
    lead_source: LeadSource
    source_campaign: str | None = None
    lead_status: LeadStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SalesLeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str = Field(..., min_length=1, max_length=150)
    contact_email: str = Field(..., min_length=1, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    interested_product: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=255)
    lead_source: LeadSource = "Shopify Website"
    source_campaign: str | None = Field(default=None, max_length=255)
    lead_status: LeadStatus = "Unfollowed"


class SalesLeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str | None = Field(default=None, min_length=1, max_length=150)
    contact_email: str | None = Field(default=None, min_length=1, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    interested_product: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=255)
    lead_source: LeadSource | None = None
    source_campaign: str | None = Field(default=None, max_length=255)
    lead_status: LeadStatus | None = None
