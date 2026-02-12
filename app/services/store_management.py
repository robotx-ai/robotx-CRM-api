from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from app.config import settings
from app.services.supabase_rest import SupabaseRestError


class StoreManagementService:
    def __init__(self) -> None:
        self._base_url = f"{settings.supabase_url}/rest/v1"
        self._headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self._headers)
        if prefer:
            headers["Prefer"] = prefer

        url = f"{self._base_url}/{table}"
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
        table: str,
        params: dict[str, Any],
    ) -> tuple[int, list[dict[str, Any]]]:
        headers = dict(self._headers)
        headers["Prefer"] = "count=exact"
        url = f"{self._base_url}/{table}"

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

    async def _find_agent_ids_by_keyword(self, keyword: str) -> list[str]:
        escaped = keyword.replace(",", "").replace("(", "").replace(")", "")
        data = await self._request(
            "GET",
            "agents",
            params={
                "select": "id",
                "or": f"(name.ilike.*{escaped}*,email.ilike.*{escaped}*)",
                "limit": 200,
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected agent lookup payload.")
        return [str(item["id"]) for item in data if item.get("id")]

    async def list_store_cards(
        self,
        *,
        keyword: str | None,
        agent_name_or_account: str | None,
        created_date: str | None,
        limit: int,
        offset: int,
        order_by: str,
    ) -> tuple[int, list[dict[str, Any]]]:
        params: dict[str, str | int] = {
            "select": "id,name,code,created_at,agent_id,agents(id,name,email,created_at)",
            "limit": limit,
            "offset": offset,
            "order": order_by,
        }

        if keyword:
            escaped = keyword.replace(",", "").replace("(", "").replace(")", "")
            params["or"] = f"(name.ilike.*{escaped}*,code.ilike.*{escaped}*)"

        if agent_name_or_account:
            agent_ids = await self._find_agent_ids_by_keyword(agent_name_or_account)
            if not agent_ids:
                return 0, []
            joined = ",".join(agent_ids)
            params["agent_id"] = f"in.({joined})"

        if created_date:
            params["and"] = (
                f"(created_at.gte.{created_date}T00:00:00Z,"
                f"created_at.lt.{created_date}T23:59:59.999Z)"
            )

        return await self._list_rows("stores", params=params)

    async def list_all_stores_for_agents(self, agent_ids: list[str]) -> list[dict[str, Any]]:
        if not agent_ids:
            return []
        joined = ",".join(agent_ids)
        data = await self._request(
            "GET",
            "stores",
            params={
                "select": "id,agent_id",
                "agent_id": f"in.({joined})",
                "limit": 10000,
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected stores payload.")
        return data

    async def list_machine_bindings(self, store_ids: list[str]) -> list[dict[str, Any]]:
        if not store_ids:
            return []
        joined = ",".join(store_ids)
        data = await self._request(
            "GET",
            "machineproductlibrary",
            params={
                "select": "store_id,status",
                "store_id": f"in.({joined})",
                "limit": 10000,
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected machine bindings payload.")
        return data

    async def get_store_by_id(self, store_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            "stores",
            params={
                "id": f"eq.{store_id}",
                "limit": 1,
                "select": "id,name,code,created_at,agent_id,agents(id,name,email,created_at)",
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected get store payload.")
        return data[0] if data else None

    async def list_agent_options(self, *, keyword: str | None, limit: int) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "select": "id,name,email",
            "order": "created_at.desc.nullslast",
            "limit": limit,
        }
        if keyword:
            escaped = keyword.replace(",", "").replace("(", "").replace(")", "")
            params["or"] = f"(name.ilike.*{escaped}*,email.ilike.*{escaped}*)"

        data = await self._request("GET", "agents", params=params)
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected list agent options payload.")
        return data

    async def ensure_agent(self, *, agent_id: str | None, agent_name: str | None) -> str | None:
        if agent_id:
            return agent_id

        if not agent_name:
            return None

        existing = await self._request(
            "GET",
            "agents",
            params={"name": f"eq.{agent_name}", "select": "id", "limit": 1},
        )
        if not isinstance(existing, list):
            raise SupabaseRestError("Unexpected find agent payload.")
        if existing:
            return str(existing[0]["id"])

        created = await self._request(
            "POST",
            "agents",
            json={"name": agent_name},
            prefer="return=representation",
        )
        if not isinstance(created, list) or not created:
            raise SupabaseRestError("Unexpected create agent payload.")
        return str(created[0]["id"])

    async def create_store(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request(
            "POST",
            "stores",
            json=payload,
            prefer="return=representation",
        )
        if not isinstance(data, list) or not data:
            raise SupabaseRestError("Unexpected create store payload.")
        return data[0]

    async def update_store(self, store_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = await self._request(
            "PATCH",
            "stores",
            params={"id": f"eq.{store_id}"},
            json=payload,
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected update store payload.")
        return data[0] if data else None

    async def delete_store(self, store_id: str) -> bool:
        data = await self._request(
            "DELETE",
            "stores",
            params={"id": f"eq.{store_id}"},
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected delete store payload.")
        return len(data) > 0

    async def build_agent_metrics(self, agent_ids: list[str]) -> dict[str, dict[str, int]]:
        stores = await self.list_all_stores_for_agents(agent_ids)
        if not stores:
            return {}

        store_ids = [str(item["id"]) for item in stores if item.get("id")]
        store_to_agent: dict[str, str] = {
            str(item["id"]): str(item["agent_id"])
            for item in stores
            if item.get("id") and item.get("agent_id")
        }

        store_counter = Counter(
            str(item["agent_id"]) for item in stores if item.get("agent_id")
        )

        machine_rows = await self.list_machine_bindings(store_ids)
        binding_counter: Counter[str] = Counter()
        for row in machine_rows:
            raw_store_id = row.get("store_id")
            if not raw_store_id:
                continue
            agent_id = store_to_agent.get(str(raw_store_id))
            if not agent_id:
                continue
            binding_counter[agent_id] += 1

        result: dict[str, dict[str, int]] = {}
        for agent_id in agent_ids:
            store_count = int(store_counter.get(agent_id, 0))
            binding_count = int(binding_counter.get(agent_id, 0))
            result[agent_id] = {
                "store_count": store_count,
                "binding_count": binding_count,
                "client_count": store_count,
            }
        return result

    @staticmethod
    def derive_status(*, binding_count: int) -> str:
        if binding_count > 0:
            return "active"
        return "inactive"

    @staticmethod
    def generate_store_code() -> str:
        now = datetime.now(UTC)
        return f"STORE-{now.strftime('%Y%m%d%H%M%S')}"

    @staticmethod
    def parse_uuid(value: UUID | str | None) -> str | None:
        if value is None:
            return None
        return str(value)
