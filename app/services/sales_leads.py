from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.supabase_rest import SupabaseRestError


class SalesLeadsService:
    def __init__(self) -> None:
        self._base_url = f"{settings.supabase_url}/rest/v1"
        self._headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        self._table = "sales_leads"

    async def _request(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer

        url = f"{self._base_url}/{self._table}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers,
            )

        if response.status_code >= 400:
            raise SupabaseRestError(
                f"Supabase REST request failed ({response.status_code}): {response.text}"
            )

        if not response.text.strip():
            return None

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    async def _list_rows(
        self,
        params: dict[str, Any],
    ) -> tuple[int, list[dict[str, Any]]]:
        headers = dict(self._headers)
        headers["Prefer"] = "count=exact"
        url = f"{self._base_url}/{self._table}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code >= 400:
            raise SupabaseRestError(
                f"Supabase REST request failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected list response payload.")

        content_range = response.headers.get("content-range", "")
        total = len(data)
        if "/" in content_range:
            try:
                total = int(content_range.rsplit("/", 1)[-1])
            except ValueError:
                total = len(data)

        return total, data

    async def list_sales_leads(
        self,
        *,
        owner_user_id: str,
        keyword: str | None,
        lead_status: str | None,
        lead_source: str | None,
        location: str | None,
        created_date: str | None,
        limit: int,
        offset: int,
        order_by: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        params: dict[str, str | int] = {
            "select": (
                "id,owner_user_id,contact_name,contact_email,phone_number,"
                "interested_product,message,location,lead_source,source_campaign,"
                "lead_status,created_at,updated_at,user_profiles(full_name,email)"
            ),
            "owner_user_id": f"eq.{owner_user_id}",
            "limit": limit,
            "offset": offset,
            "order": order_by,
        }

        if keyword:
            escaped = self.escape_keyword(keyword)
            params["or"] = (
                f"(contact_name.ilike.*{escaped}*,contact_email.ilike.*{escaped}*,"
                f"phone_number.ilike.*{escaped}*,interested_product.ilike.*{escaped}*,"
                f"message.ilike.*{escaped}*)"
            )

        if lead_status:
            params["lead_status"] = f"eq.{lead_status}"
        if lead_source:
            params["lead_source"] = f"eq.{lead_source}"
        if location:
            escaped_location = self.escape_keyword(location)
            params["location"] = f"ilike.*{escaped_location}*"
        if created_date:
            params["and"] = (
                f"(created_at.gte.{created_date}T00:00:00Z,"
                f"created_at.lt.{created_date}T23:59:59.999Z)"
            )

        return await self._list_rows(params=params)

    async def get_sales_lead(self, *, lead_id: str, owner_user_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            params={
                "id": f"eq.{lead_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 1,
                "select": (
                    "id,owner_user_id,contact_name,contact_email,phone_number,"
                    "interested_product,message,location,lead_source,source_campaign,"
                    "lead_status,created_at,updated_at"
                ),
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected get sales lead payload.")
        return data[0] if data else None

    async def create_sales_lead(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request(
            "POST",
            json=payload,
            prefer="return=representation",
        )
        if not isinstance(data, list) or not data:
            raise SupabaseRestError("Unexpected create sales lead payload.")
        return data[0]

    async def update_sales_lead(
        self,
        *,
        lead_id: str,
        owner_user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        data = await self._request(
            "PATCH",
            params={"id": f"eq.{lead_id}", "owner_user_id": f"eq.{owner_user_id}"},
            json=payload,
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected update sales lead payload.")
        return data[0] if data else None

    async def delete_sales_lead(self, *, lead_id: str, owner_user_id: str) -> bool:
        data = await self._request(
            "DELETE",
            params={"id": f"eq.{lead_id}", "owner_user_id": f"eq.{owner_user_id}"},
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected delete sales lead payload.")
        return len(data) > 0

    @staticmethod
    def parse_owner_user_id(value: str | None) -> str | None:
        if not value:
            return None
        return value.strip() or None

    @staticmethod
    def escape_keyword(keyword: str) -> str:
        return keyword.replace(",", "").replace("(", "").replace(")", "")
