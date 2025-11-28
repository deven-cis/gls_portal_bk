from fastapi import APIRouter

from src.auth.schema import TokenResponseSchema
from src.core.utils import get_response_schema
from src.auth.apis import login_user, refresh_token

auth_router = APIRouter()

auth_router.add_api_route(
    '/login',
    login_user,
    methods=['POST'],
    responses=get_response_schema(
        TokenResponseSchema,
        200
    ),
)
auth_router.add_api_route(
    '/refresh-token',
    refresh_token,
    methods=['POST'],
    responses=get_response_schema(
        TokenResponseSchema,
        200
    ),
)