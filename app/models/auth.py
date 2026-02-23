from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


OrganizationRole = Literal['owner', 'admin', 'member']


class AuthSignupCompleteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: str = Field(..., min_length=3, max_length=320)
    full_name: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=8, max_length=255)


class AuthSignupCompleteResponse(BaseModel):
    user_id: UUID
    email: str
    requires_email_verification: bool = True


class AuthOrganizationOption(BaseModel):
    organization_id: UUID
    organization_name: str
    role: OrganizationRole


class AuthOrganizationOptionListResponse(BaseModel):
    total: int
    items: list[AuthOrganizationOption]
