from fastapi import APIRouter
from src.auth.schema import TokenResponseSchema
from src.core.utils import get_response_schema
from src.auth import apis

auth_router = APIRouter(tags=["authentication"])

auth_router.add_api_route(
    '/login',
    apis.login_user,
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
    apis.refresh_token,
    methods=['POST'],
    responses=get_response_schema(
        TokenResponseSchema,
        200
    ),
)

auth_router.add_api_route(
    '/forget-password',
    apis.forget_password,
    methods=['POST'],
)

auth_router.add_api_route(
    '/reset-password',
    apis.reset_password,
    methods=["POST"]
)

