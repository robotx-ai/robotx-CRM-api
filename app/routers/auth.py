from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from app.models.auth import (
    AuthOrganizationOption,
    AuthOrganizationOptionListResponse,
    AuthSignupCompleteRequest,
    AuthSignupCompleteResponse,
)
from app.routers._auth import parse_user_id_or_401
from app.services.auth import AuthService
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix='/auth', tags=['Auth'])
service = AuthService()


@router.get(
    '/organization-options',
    response_model=AuthOrganizationOptionListResponse,
    summary='List organizations for current user',
)
async def list_organization_options(
    x_robotx_user_id: str | None = Header(default=None, alias='x-robotx-user-id'),
) -> AuthOrganizationOptionListResponse:
    user_id = parse_user_id_or_401(x_robotx_user_id)

    try:
        items = await service.list_user_organizations(user_id=user_id)
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AuthOrganizationOptionListResponse(
        total=len(items),
        items=[AuthOrganizationOption(**item) for item in items],
    )


@router.post(
    '/signup/complete',
    response_model=AuthSignupCompleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Open email signup',
)
async def complete_signup(payload: AuthSignupCompleteRequest) -> AuthSignupCompleteResponse:
    try:
        result = await service.complete_signup(
            email=payload.email,
            full_name=payload.full_name,
            password=payload.password,
        )
    except ValueError as exc:
        reason = str(exc)
        reason_to_response: dict[str, tuple[int, str]] = {
            'invalid_email': (400, 'Invalid email'),
            'invalid_full_name': (400, 'Invalid full name'),
            'weak_password': (400, 'Password does not meet requirements'),
            'email_exists': (409, 'Email is already registered'),
        }
        status_code, detail = reason_to_response.get(reason, (400, 'Invalid signup request'))
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except SupabaseRestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AuthSignupCompleteResponse(
        user_id=UUID(result['user_id']),
        email=result['email'],
        requires_email_verification=bool(result['requires_email_verification']),
    )
