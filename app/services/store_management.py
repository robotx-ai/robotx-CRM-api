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

    async def list_store_cards(
        self,
        *,
        owner_user_id: str,
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
            "owner_user_id": f"eq.{owner_user_id}",
        }

        if keyword:
            escaped = keyword.replace(",", "").replace("(", "").replace(")", "")
            params["or"] = f"(name.ilike.*{escaped}*,code.ilike.*{escaped}*)"

        if created_date:
            params["and"] = (
                f"(created_at.gte.{created_date}T00:00:00Z,"
                f"created_at.lt.{created_date}T23:59:59.999Z)"
            )

        total, rows = await self._list_rows("stores", params=params)
        if not agent_name_or_account:
            return total, rows

        agent_keyword = agent_name_or_account.strip().lower()
        filtered_rows = []
        for row in rows:
            agent = row.get("agents") or {}
            if isinstance(agent, list):
                agent = agent[0] if agent else {}
            haystack = f"{agent.get('name', '')} {agent.get('email', '')}".lower()
            if agent_keyword in haystack:
                filtered_rows.append(row)

        return len(filtered_rows), filtered_rows

    async def list_all_stores_for_agents(
        self, agent_ids: list[str], *, owner_user_id: str
    ) -> list[dict[str, Any]]:
        if not agent_ids:
            return []
        joined = ",".join(agent_ids)
        data = await self._request(
            "GET",
            "stores",
            params={
                "select": "id,agent_id",
                "agent_id": f"in.({joined})",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 10000,
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected stores payload.")
        return data

    async def list_machine_bindings(
        self, store_ids: list[str], *, owner_user_id: str
    ) -> list[dict[str, Any]]:
        if not store_ids:
            return []
        joined = ",".join(store_ids)
        data = await self._request(
            "GET",
            "machineproductlibrary",
            params={
                "select": "store_id,status",
                "store_id": f"in.({joined})",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 10000,
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected machine bindings payload.")
        return data

    async def get_store_by_id(self, store_id: str, *, owner_user_id: str) -> dict[str, Any] | None:
        data = await self._request(
            "GET",
            "stores",
            params={
                "id": f"eq.{store_id}",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 1,
                "select": "id,name,code,created_at,agent_id,agents(id,name,email,created_at)",
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected get store payload.")
        return data[0] if data else None

    async def list_agent_options(
        self,
        *,
        owner_user_id: str,
        keyword: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        owned_stores = await self._request(
            "GET",
            "stores",
            params={
                "select": "agent_id",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 10000,
            },
        )
        if not isinstance(owned_stores, list):
            raise SupabaseRestError("Unexpected owned stores payload.")
        owned_agent_ids = sorted(
            {str(row.get("agent_id")) for row in owned_stores if row.get("agent_id")}
        )

        params: dict[str, str | int] = {
            "select": "id,name,email",
            "order": "created_at.desc.nullslast",
            "limit": 1000,
        }
        if owned_agent_ids:
            params["or"] = f"(user_id.eq.{owner_user_id},id.in.({','.join(owned_agent_ids)}))"
        else:
            params["user_id"] = f"eq.{owner_user_id}"

        data = await self._request("GET", "agents", params=params)
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected list agent options payload.")

        if keyword:
            keyword_lower = keyword.strip().lower()
            data = [
                row
                for row in data
                if keyword_lower
                in f"{row.get('name', '')} {row.get('email', '')}".lower()
            ]

        return data[:limit]

    async def list_subordinate_agents(
        self,
        *,
        owner_user_id: str,
        keyword: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        owned_stores = await self._request(
            "GET",
            "stores",
            params={
                "select": "id,agent_id",
                "owner_user_id": f"eq.{owner_user_id}",
                "limit": 10000,
            },
        )
        if not isinstance(owned_stores, list):
            raise SupabaseRestError("Unexpected owned stores payload.")

        owned_agent_ids = sorted(
            {str(row.get("agent_id")) for row in owned_stores if row.get("agent_id")}
        )
        store_ids = [str(row.get("id")) for row in owned_stores if row.get("id")]
        store_to_agent: dict[str, str] = {
            str(row["id"]): str(row["agent_id"])
            for row in owned_stores
            if row.get("id") and row.get("agent_id")
        }
        store_counter = Counter(
            str(row["agent_id"]) for row in owned_stores if row.get("agent_id")
        )

        binding_counter: Counter[str] = Counter()
        machine_rows = await self.list_machine_bindings(store_ids, owner_user_id=owner_user_id)
        for row in machine_rows:
            raw_store_id = row.get("store_id")
            if not raw_store_id:
                continue
            agent_id = store_to_agent.get(str(raw_store_id))
            if agent_id:
                binding_counter[agent_id] += 1

        params: dict[str, str | int] = {
            "select": "id,name,email,created_at,user_id",
            "order": "created_at.desc.nullslast",
            "limit": 1000,
        }
        if owned_agent_ids:
            params["or"] = f"(user_id.eq.{owner_user_id},id.in.({','.join(owned_agent_ids)}))"
        else:
            params["user_id"] = f"eq.{owner_user_id}"

        agent_rows = await self._request("GET", "agents", params=params)
        if not isinstance(agent_rows, list):
            raise SupabaseRestError("Unexpected subordinate agents payload.")

        if owned_agent_ids:
            agent_ids_in_payload = {str(row.get("id")) for row in agent_rows if row.get("id")}
            missing_owned_ids = [agent_id for agent_id in owned_agent_ids if agent_id not in agent_ids_in_payload]
            for missing_id in missing_owned_ids:
                agent_rows.append({"id": missing_id, "name": missing_id, "email": None, "created_at": None})

        keyword_value = keyword.strip().lower() if keyword else None
        status_value = status.strip().lower() if status else None

        items: list[dict[str, Any]] = []
        for row in agent_rows:
            raw_agent_id = row.get("id")
            if not raw_agent_id:
                continue
            agent_id = str(raw_agent_id)
            store_count = int(store_counter.get(agent_id, 0))
            binding_count = int(binding_counter.get(agent_id, 0))
            row_status = self.derive_status(binding_count=binding_count)

            if status_value and row_status != status_value:
                continue

            agent_name = str(row.get("name") or "").strip() or f"Agent {agent_id[:8]}"
            proxy_account = row.get("email")
            if keyword_value:
                haystack = f"{agent_name} {proxy_account or ''}".lower()
                if keyword_value not in haystack:
                    continue

            items.append(
                {
                    "agent_id": agent_id,
                    "agent_company_name": agent_name,
                    "proxy_account": proxy_account,
                    "client_count": store_count,
                    "company_location": None,
                    "sales_area": None,
                    "store_count": store_count,
                    "binding_count": binding_count,
                    "superior_agent_name": None,
                    "created_at": row.get("created_at"),
                    "status": row_status,
                }
            )

        items.sort(
            key=lambda item: (
                item.get("created_at") is None,
                item.get("created_at") or "",
            ),
            reverse=True,
        )
        total = len(items)
        return total, items[offset : offset + limit]

    async def ensure_agent(
        self,
        *,
        owner_user_id: str,
        agent_id: str | None,
        agent_name: str | None,
    ) -> str | None:
        if agent_id:
            existing = await self._request(
                "GET",
                "agents",
                params={
                    "id": f"eq.{agent_id}",
                    "select": "id,user_id",
                    "limit": 1,
                },
            )
            if not isinstance(existing, list):
                raise SupabaseRestError("Unexpected find agent payload.")
            if not existing:
                return None
            agent_user_id = existing[0].get("user_id")
            if agent_user_id and str(agent_user_id) != owner_user_id:
                return None
            if not agent_user_id:
                linked_store = await self._request(
                    "GET",
                    "stores",
                    params={
                        "select": "id",
                        "owner_user_id": f"eq.{owner_user_id}",
                        "agent_id": f"eq.{agent_id}",
                        "limit": 1,
                    },
                )
                if not isinstance(linked_store, list):
                    raise SupabaseRestError("Unexpected linked store lookup payload.")
                if not linked_store:
                    return None
            return agent_id

        if not agent_name:
            return None

        existing = await self._request(
            "GET",
            "agents",
            params={
                "name": f"eq.{agent_name}",
                "user_id": f"eq.{owner_user_id}",
                "select": "id",
                "limit": 1,
            },
        )
        if not isinstance(existing, list):
            raise SupabaseRestError("Unexpected find agent payload.")
        if existing:
            return str(existing[0]["id"])

        created = await self._request(
            "POST",
            "agents",
            json={"name": agent_name, "user_id": owner_user_id},
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

    async def update_store(
        self,
        store_id: str,
        *,
        owner_user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        data = await self._request(
            "PATCH",
            "stores",
            params={"id": f"eq.{store_id}", "owner_user_id": f"eq.{owner_user_id}"},
            json=payload,
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected update store payload.")
        return data[0] if data else None

    async def delete_store(self, store_id: str, *, owner_user_id: str) -> bool:
        data = await self._request(
            "DELETE",
            "stores",
            params={"id": f"eq.{store_id}", "owner_user_id": f"eq.{owner_user_id}"},
            prefer="return=representation",
        )
        if not isinstance(data, list):
            raise SupabaseRestError("Unexpected delete store payload.")
        return len(data) > 0

    async def build_agent_metrics(
        self, agent_ids: list[str], *, owner_user_id: str
    ) -> dict[str, dict[str, int]]:
        stores = await self.list_all_stores_for_agents(agent_ids, owner_user_id=owner_user_id)
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

        machine_rows = await self.list_machine_bindings(store_ids, owner_user_id=owner_user_id)
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
    def derive_status(
        *,
        binding_count: int,
        authorization_code: str | None = None,
        store_name: str | None = None,
    ) -> str:
        # Allow mock status for demo/testing scenarios without changing DB schema.
        hint = f"{authorization_code or ''} {store_name or ''}".lower()
        if "pending" in hint:
            return "pending"
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
