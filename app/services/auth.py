from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.services.supabase_rest import SupabaseRestError


class AuthService:
    def __init__(self) -> None:
        self._rest_url = f'{settings.supabase_url}/rest/v1'
        self._service_headers = {
            'apikey': settings.supabase_service_role_key,
            'Authorization': f'Bearer {settings.supabase_service_role_key}',
            'Content-Type': 'application/json',
        }
        self._anon_headers = {
            'apikey': settings.supabase_anon_key,
            'Authorization': f'Bearer {settings.supabase_anon_key}',
            'Content-Type': 'application/json',
        }

    async def _request(
        self,
        method: str,
        *,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[dict[str, Any]] | None = None,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self._service_headers)
        if prefer:
            headers['Prefer'] = prefer

        url = f"{self._rest_url}/{path.lstrip('/')}"

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
                f'Supabase REST request failed ({response.status_code}): {response.text}'
            )

        if not response.text.strip():
            return None

        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            return response.json()
        return response.text

    async def _auth_signup_request(self, *, email: str, password: str, full_name: str) -> dict[str, Any]:
        url = f'{settings.supabase_url}/auth/v1/signup'
        payload = {
            'email': email,
            'password': password,
            'data': {
                'full_name': full_name,
                'name': full_name,
            },
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload, headers=self._anon_headers)

        if response.status_code >= 400:
            message = response.text.lower()
            if 'already registered' in message or 'already been registered' in message:
                raise ValueError('email_exists')
            raise SupabaseRestError(
                f'Supabase auth signup request failed ({response.status_code}): {response.text}'
            )

        if not response.text.strip():
            raise SupabaseRestError('Supabase auth signup returned an empty response.')

        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type:
            raise SupabaseRestError('Supabase auth signup returned non-JSON response.')

        data = response.json()
        if not isinstance(data, dict):
            raise SupabaseRestError('Unexpected auth signup payload.')
        return data

    async def _email_exists_in_profiles(self, *, email: str) -> bool:
        data = await self._request(
            'GET',
            path='user_profiles',
            params={
                'select': 'id',
                'email': f'eq.{email}',
                'limit': 1,
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError('Unexpected user profile lookup payload.')
        return len(data) > 0

    async def complete_signup(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
    ) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        normalized_name = full_name.strip()

        if not normalized_email or '@' not in normalized_email:
            raise ValueError('invalid_email')
        if not normalized_name:
            raise ValueError('invalid_full_name')
        if len(password) < 8:
            raise ValueError('weak_password')

        if await self._email_exists_in_profiles(email=normalized_email):
            raise ValueError('email_exists')

        auth_data = await self._auth_signup_request(
            email=normalized_email,
            password=password,
            full_name=normalized_name,
        )

        # Supabase signup payload can be either:
        # 1) {"user": {...}, "session": ...}
        # 2) top-level user object with "id"/"email" fields
        user: dict[str, Any] | None = None
        if isinstance(auth_data, dict):
            nested_user = auth_data.get('user')
            if isinstance(nested_user, dict):
                user = nested_user
            elif auth_data.get('id'):
                user = auth_data

        if not isinstance(user, dict) or not user.get('id'):
            raise SupabaseRestError('Unexpected auth signup payload.')

        user_id = str(user['id'])

        await self._request(
            'POST',
            path='user_profiles',
            json={
                'id': user_id,
                'email': normalized_email,
                'full_name': normalized_name,
            },
            prefer='resolution=merge-duplicates,return=minimal',
        )

        return {
            'user_id': user_id,
            'email': normalized_email,
            'requires_email_verification': True,
        }

    async def list_user_organizations(self, *, user_id: str) -> list[dict[str, Any]]:
        data = await self._request(
            'GET',
            path='organization_memberships',
            params={
                'select': 'organization_id,role,status,organizations(name)',
                'user_id': f'eq.{user_id}',
                'status': 'eq.active',
                'order': 'created_at.asc',
            },
        )
        if not isinstance(data, list):
            raise SupabaseRestError('Unexpected organization membership payload.')

        items: list[dict[str, Any]] = []
        for row in data:
            organization = row.get('organizations') or {}
            if isinstance(organization, list):
                organization = organization[0] if organization else {}

            org_id = row.get('organization_id')
            org_name = organization.get('name')
            role = row.get('role')
            if not org_id or not org_name or not role:
                continue
            items.append(
                {
                    'organization_id': org_id,
                    'organization_name': org_name,
                    'role': role,
                }
            )

        return items
