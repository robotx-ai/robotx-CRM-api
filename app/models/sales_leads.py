from __future__ import annotations

from datetime import datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LeadStatus = Literal[
    "Unfollowed",
    "Following Up",
    "Converted",
    "Lost",
    "Followed but No Reply",
    "Followed with Reply",
    "Sales Pending",
    "Sales Rejected",
]
LeadSource = Literal[
    "Sales Email",
    "Shopify Website",
    "Referral",
    "Manufacturer Referral",
]
CustomerType = Literal["Education", "Individual", "Warehouse", "Hotel", "Hospital"]

_ZIP_CODE_RE = re.compile(r"^\d{5}(-\d{4})?$")


class SalesLeadListItem(BaseModel):
    id: UUID
    owner_user_id: UUID
    contact_name: str
    contact_email: str
    phone_number: str | None = None
    organization_name: str
    customer_type: CustomerType
    interested_product: str | None = None
    message: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    lead_source: LeadSource
    referrer_name: str | None = None
    referrer_phone: str | None = None
    referrer_email: str | None = None
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
    organization_name: str
    customer_type: CustomerType
    interested_product: str | None = None
    message: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    lead_source: LeadSource
    referrer_name: str | None = None
    referrer_phone: str | None = None
    referrer_email: str | None = None
    source_campaign: str | None = None
    lead_status: LeadStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SalesLeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str = Field(..., min_length=1, max_length=150)
    contact_email: str = Field(..., min_length=1, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    organization_name: str = Field(..., min_length=1, max_length=255)
    customer_type: CustomerType
    interested_product: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=50)
    zip_code: str | None = Field(default=None, max_length=10)
    lead_source: LeadSource = "Shopify Website"
    referrer_name: str | None = Field(default=None, max_length=150)
    referrer_phone: str | None = Field(default=None, max_length=50)
    referrer_email: str | None = Field(default=None, max_length=320)
    source_campaign: str | None = Field(default=None, max_length=255)
    lead_status: LeadStatus = "Unfollowed"

    @field_validator("phone_number", "referrer_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        digits = "".join(ch for ch in stripped if ch.isdigit())
        if len(digits) != 10:
            raise ValueError("Phone number must contain exactly 10 digits")
        return digits

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if not _ZIP_CODE_RE.fullmatch(stripped):
            raise ValueError("ZIP code must be in 12345 or 12345-6789 format")
        return stripped

    @model_validator(mode="after")
    def validate_referral_requirements(self) -> "SalesLeadCreate":
        if self.lead_source == "Referral":
            if not self.referrer_name or not self.referrer_name.strip():
                raise ValueError("referrer_name is required when lead_source is Referral")
            if not self.referrer_phone:
                raise ValueError("referrer_phone is required when lead_source is Referral")
            if not self.referrer_email or not self.referrer_email.strip():
                raise ValueError("referrer_email is required when lead_source is Referral")
        return self


class SalesLeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_name: str | None = Field(default=None, min_length=1, max_length=150)
    contact_email: str | None = Field(default=None, min_length=1, max_length=320)
    phone_number: str | None = Field(default=None, max_length=50)
    organization_name: str | None = Field(default=None, min_length=1, max_length=255)
    customer_type: CustomerType | None = None
    interested_product: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=4000)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=50)
    zip_code: str | None = Field(default=None, max_length=10)
    lead_source: LeadSource | None = None
    referrer_name: str | None = Field(default=None, max_length=150)
    referrer_phone: str | None = Field(default=None, max_length=50)
    referrer_email: str | None = Field(default=None, max_length=320)
    source_campaign: str | None = Field(default=None, max_length=255)
    lead_status: LeadStatus | None = None

    @field_validator("phone_number", "referrer_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        digits = "".join(ch for ch in stripped if ch.isdigit())
        if len(digits) != 10:
            raise ValueError("Phone number must contain exactly 10 digits")
        return digits

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if not _ZIP_CODE_RE.fullmatch(stripped):
            raise ValueError("ZIP code must be in 12345 or 12345-6789 format")
        return stripped

    @model_validator(mode="after")
    def validate_referral_requirements(self) -> "SalesLeadUpdate":
        if self.lead_source == "Referral":
            if not self.referrer_name or not self.referrer_name.strip():
                raise ValueError("referrer_name is required when lead_source is Referral")
            if not self.referrer_phone:
                raise ValueError("referrer_phone is required when lead_source is Referral")
            if not self.referrer_email or not self.referrer_email.strip():
                raise ValueError("referrer_email is required when lead_source is Referral")
        return self
