from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.utils import get_current_user
from src.core.database import get_db
from src.core.context import get_context
from src.users import apis
from src.auth.schema import PasswordChangeSchema

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("/current_user", status_code=200)
async def get_current_user_profile(
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
    return await apis.get_current_user_profile(int(user_id), db)


@users_router.post("/profile-picture", status_code=200)
async def upload_profile_picture(
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
    return await apis.upload_profile_picture(int(user_id), file, db)


@users_router.delete("/profile-picture", status_code=200)
async def remove_profile_picture(
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
    return await apis.remove_profile_picture(int(user_id), db)


@users_router.post("/change-password", status_code=200)
async def change_password(
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
    return await apis.change_password(schema, int(user_id), db)


@users_router.get("/assignee-users-list", status_code=200)
async def assignee_users_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    return await apis.assignee_users_list(db)

