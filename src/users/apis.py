import json
import time as _time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.auth.utils import get_current_user
from src.core.context import get_context
from src.core.database import get_db
from src.core.file_utils import save_image_file
from src.core.logger import logger
from src.users.models import Users
from src.users.schema import UserResponseSchema
from src.users.utils import hash_password, verify_password
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
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "success": False,
                "result": {"message": "Invalid token payload (missing user id)"},
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = db.query(Users).filter(Users.id == int(user_id), ~Users.is_archived).first()
    if not user:
        return JSONResponse(
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "success": False,
                "result": {"message": "User not found"},
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return JSONResponse(
        content={
            "status_code": status.HTTP_200_OK,
            "success": True,
            "result": UserResponseSchema.model_validate(user).model_dump(mode="json"),
        },
        status_code=status.HTTP_200_OK,
    )


@users_router.post("/profile-picture", status_code=200)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Upload a new profile picture for the current user.
    """
    user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
    entered_by = get_context("entered_by") or 0
    now = datetime.utcnow()

    if not user_id:
        return JSONResponse(
            content={
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "success": False,
                "result": {"message": "Not authenticated"},
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        user = db.query(Users).filter(Users.id == int(user_id), ~Users.is_archived).first()
        if not user:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "User not found"},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # If replacing an existing picture, delete old file (best-effort)
        old_path = user.profile_image_url

        orig_name, path = await save_image_file(file, "profile_pictures")

        user.profile_image_url = path
        user.last_modified_at = now
        user.last_modified_by = entered_by
        db.commit()
        db.refresh(user)

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": UserResponseSchema.model_validate(user).model_dump(mode="json"),
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error("Error uploading profile picture: %s", str(e), exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Failed to upload profile picture"},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@users_router.delete("/profile-picture", status_code=200)
async def remove_profile_picture(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Remove the current user's profile picture:
    - deletes the file on disk (best-effort)
    - sets Users.profile_image_url = NULL
    """
    user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
    entered_by = get_context("entered_by") or 0
    now = datetime.utcnow()

    if not user_id:
        return JSONResponse(
            content={
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "success": False,
                "result": {"message": "Not authenticated"},
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        user = db.query(Users).filter(Users.id == int(user_id), ~Users.is_archived).first()
        if not user:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "User not found"},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        old_path = user.profile_image_url
        user.profile_image_url = None
        user.last_modified_at = now
        user.last_modified_by = entered_by
        db.commit()
        db.refresh(user)

        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": UserResponseSchema.model_validate(user).model_dump(mode="json"),
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error("Error removing profile picture: %s", str(e), exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Failed to remove profile picture"},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@users_router.post("/change-password", status_code=200)
async def change_password(
    schema: PasswordChangeSchema,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Change Password API
    """
    try:
        user_id = current_user.get("id") or current_user.get("user_id") or get_context("user_id")
        if not user_id:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Not authenticated"},
                },
                status_code=status.HTTP_200_OK,
            )

        # Use user_id from token if not provided in schema, or validate schema user_id matches token
        if schema.user_id != int(user_id):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "success": False,
                    "result": {"message": "You can only change your own password"},
                },
                status_code=status.HTTP_200_OK,
            )

        user = Users.get(schema.user_id)
 
        if not user:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "User not found"},
                },
                status_code=status.HTTP_200_OK,
            )
        
        if not verify_password(schema.old_password, user.login_password):
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "success": False,
                    "result": {"message": "Old password is incorrect"},
                },
                status_code=status.HTTP_200_OK,
            )
        
        user.login_password = hash_password(schema.new_password)
        user.require_password_change = False
        user.save()
 
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": {"message": "Password changed successfully"},
            },
            status_code=status.HTTP_200_OK,
        )
 
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Error changing password"},
            },
            status_code=status.HTTP_200_OK,
        )



@users_router.get("/assignee-users-list", status_code=200)
async def assignee_users_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    try:
        list_of_users = db.query(Users).filter(Users.is_archived == False).all()
        logger.info(f"List of users: {list_of_users}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": [UserResponseSchema.model_validate(user).model_dump(mode="json") for user in list_of_users],
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(f"Error getting list of users: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": [],
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )