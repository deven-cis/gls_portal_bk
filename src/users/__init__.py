from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.core.context import get_context
from src.users.apis import get_current_user_profile, upload_profile_picture, remove_profile_picture, change_password, assignee_users_list
from src.auth.schema import PasswordChangeSchema

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/current_user", status_code=200)
async def get_current_user_profile_endpoint(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
    if not user_id:
        return JSONResponse(
            content={
                "status_code": 401,
                "success": False,
                "result": {"message": "Invalid token payload (missing user id)"},
            },
            status_code=401,
        )
    return await get_current_user_profile(int(user_id), db)


@users_router.post("/profile-picture", status_code=200)
async def upload_profile_picture_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
    if not user_id:
        return JSONResponse(
            content={
                "status_code": 401,
                "success": False,
                "result": {"message": "Not authenticated"},
            },
            status_code=401,
        )
    return await upload_profile_picture(int(user_id), file, db)


@users_router.delete("/profile-picture", status_code=200)
async def remove_profile_picture_endpoint(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
    if not user_id:
        return JSONResponse(
            content={
                "status_code": 401,
                "success": False,
                "result": {"message": "Not authenticated"},
            },
            status_code=401,
        )
    return await remove_profile_picture(int(user_id), db)


@users_router.post("/change-password", status_code=200)
async def change_password_endpoint(
    schema: PasswordChangeSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
    if not user_id:
        return JSONResponse(
            content={
                "status_code": 401,
                "success": False,
                "result": {"message": "Not authenticated"},
            },
            status_code=200,
        )
    return await change_password(schema, int(user_id), db)


@users_router.get("/assignee-users-list", status_code=200)
async def assignee_users_list_endpoint(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await assignee_users_list(db)

