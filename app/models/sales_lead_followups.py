from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SalesLeadFollowupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(..., min_length=1, max_length=4000)


class SalesLeadFollowupRead(BaseModel):
    id: UUID
    sales_lead_id: UUID
    owner_user_id: UUID
    note: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SalesLeadFollowupListResponse(BaseModel):
    total: int
    items: list[SalesLeadFollowupRead]
