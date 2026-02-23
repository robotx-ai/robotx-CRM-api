from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class SupabaseRestError(RuntimeError):
    pass


class SupabaseRestClient:
    def __init__(self) -> None:
        self._base_url = f"{settings.supabase_url}/rest/v1"
        self._headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        self._table = "machineproductlibrary"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers = dict(self._headers)
        if extra_headers:
            headers.update(extra_headers)

        url = f"{self._base_url}/{path.lstrip('/')}"

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

    async def list_rows(
        self,
        params: dict[str, Any],
        *,
        owner_user_id: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        scoped_params = dict(params)
        scoped_params["owner_user_id"] = f"eq.{owner_user_id}"
        url = f"{self._base_url}/{self._table}"
        headers = dict(self._headers)
        headers["Prefer"] = "count=exact"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=scoped_params, headers=headers)

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

    async def get_by_id(self, row_id: str, *, owner_user_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            self._table,
            params={
                "id": f"eq.{row_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 1,
                "select": "*",
            },
        )
        if not data:
            return None
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected get response payload.")
        return data[0] if data else None

    async def get_by_sn(self, sn_pid: str, *, owner_user_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            self._table,
            params={
                "sn_pid": f"eq.{sn_pid}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 1,
                "select": "*",
            },
        )
        if not data:
            return None
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected get response payload.")
        return data[0] if data else None

    async def create_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request(
            "POST",
            self._table,
            json=payload,
            extra_headers={"Prefer": "return=representation"},
        )
        if not isinstance(data, list) or not data:
            raise SupabaseRestError("Unexpected create response payload.")
        return data[0]

    async def update_row(
        self,
        row_id: str,
        payload: dict[str, Any],
        *,
        owner_user_id: str,
    ) -> dict[str, Any] | None:
        data = await self._request(
            "PATCH",
            self._table,
            params={"id": f"eq.{row_id}", "owner_user_id": f"eq.{owner_user_id}"},
            json=payload,
            extra_headers={"Prefer": "return=representation"},
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected update response payload.")
        return data[0] if data else None

    async def delete_row(self, row_id: str, *, owner_user_id: str) -> bool:
        data = await self._request(
            "DELETE",
            self._table,
            params={"id": f"eq.{row_id}", "owner_user_id": f"eq.{owner_user_id}"},
            extra_headers={"Prefer": "return=representation"},
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected delete response payload.")
        return len(data) > 0
