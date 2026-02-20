from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.supabase_rest import SupabaseRestError


class SalesLeadFollowupsService:
    def __init__(self) -> None:
        self._base_url = f"{settings.supabase_url}/rest/v1"
        self._headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        self._table = "sales_lead_followups"
        self._leads_table = "sales_leads"

    async def _request(
        self,
        method: str,
        *,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer

        url = f"{self._base_url}/{path}"

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
        *,
        path: str,
        params: dict[str, Any],
    ) -> tuple[int, list[dict[str, Any]]]:
        headers = dict(self._headers)
        headers["Prefer"] = "count=exact"
        url = f"{self._base_url}/{path}"

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

    async def lead_exists_for_owner(self, *, lead_id: str, owner_user_id: str) -> bool:
        data = await self._request(
            "GET",
            path=self._leads_table,
            params={
                "id": f"eq.{lead_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 1,
                "select": "id",
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected lead lookup payload.")
        return len(data) > 0

    async def list_followups(
        self,
        *,
        owner_user_id: str,
        lead_id: str,
        limit: int,
        offset: int,
        order_by: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        params: dict[str, str | int] = {
            "select": "id,sales_lead_id,owner_user_id,note,created_at,updated_at",
            "owner_user_id": f"eq.{owner_user_id}",
            "sales_lead_id": f"eq.{lead_id}",
            "limit": limit,
            "offset": offset,
            "order": order_by,
        }
        return await self._list_rows(path=self._table, params=params)

    async def get_followup(
        self,
        *,
        followup_id: str,
        lead_id: str,
        owner_user_id: str,
    ) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            path=self._table,
            params={
                "id": f"eq.{followup_id}",
                "sales_lead_id": f"eq.{lead_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 1,
                "select": "id,sales_lead_id,owner_user_id,note,created_at,updated_at",
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected get follow-up payload.")
        return data[0] if data else None

    async def create_followup(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request(
            "POST",
            path=self._table,
            json=payload,
            prefer="return=representation",
        )
        if not isinstance(data, list) or not data:
            raise SupabaseRestError("Unexpected create follow-up payload.")
        return data[0]

    async def delete_followup(
        self,
        *,
        followup_id: str,
        lead_id: str,
        owner_user_id: str,
    ) -> bool:
        data = await self._request(
            "DELETE",
            path=self._table,
            params={
                "id": f"eq.{followup_id}",
                "sales_lead_id": f"eq.{lead_id}",
                "owner_user_id": f"eq.{owner_user_id}",
            },
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected delete follow-up payload.")
        return len(data) > 0
