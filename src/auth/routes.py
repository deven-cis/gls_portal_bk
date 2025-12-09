from fastapi import APIRouter

from src.auth.schema import TokenResponseSchema, LogoutResponseSchema
from src.core.utils import get_response_schema
from src.auth.apis import login_user, refresh_token, logout_user
from src.auth.apis import forget_password, reset_password

auth_router = APIRouter(tags=["authentication"])

auth_router.add_api_route(
    '/login',
    login_user,
    methods=['POST'],
    response_model=TokenResponseSchema,
    responses={
        200: {"description": "Successful login"},
        401: {"description": "Invalid credentials"}
    },
    summary="User Login",
    description="Authenticate user and return access token",
    operation_id="login"
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

auth_router.add_api_route(
    '/forget-password',
    forget_password,
    methods=['POST'],
)
auth_router.add_api_route(
    '/reset-password',
    reset_password,
    methods=["POST"]
)

auth_router.add_api_route(
    '/logout',
    logout_user,
    methods=['POST'],
    response_model=LogoutResponseSchema,
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Invalid or missing token"}
    },
    summary="User Logout",
    description="Logout user and invalidate token",
    operation_id="logout"
)
 