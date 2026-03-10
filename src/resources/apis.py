from src.core.timezone_utils import get_timezone_now
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.core.context import get_context
from src.core.file_utils import save_image_file
from src.core.logger import logger
from src.resources.models import Resources
from src.resources.schema import ResourceResponseSchema
from src.resources.utils import hash_password, verify_password
from src.auth.schema import PasswordChangeSchema


async def get_current_user_profile(rsrc_no: int, db: Session) -> JSONResponse:

    try:
        resource = db.query(Resources).filter(Resources.rsrc_no == rsrc_no, ~Resources.is_archived).first()
        if not resource:
            logger.info("resource not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "Resource not found"},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )
        resource_data = ResourceResponseSchema.model_validate(resource).model_dump(mode="json")
        logger.info(
            f"get current resource profile success for resource: {resource.email} (ID: {resource.id})"
        )
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": resource_data,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(f"Error getting current resource profile for resource {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Failed to get current resource profile"},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  
        )

async def upload_profile_picture(rsrc_no: int, file: UploadFile, db: Session) -> JSONResponse:
    current_rsrc_no = get_context("rsrc_no")
    now = get_timezone_now()
    try:
        resource = db.query(Resources).filter(Resources.rsrc_no == current_rsrc_no, ~Resources.is_archived).first()
        if not resource:
            logger.info("resource not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "Resource not found"},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        orig_name, path = await save_image_file(file, "profile_pictures")

        resource.profile_image_url = path
        resource.last_modified_at = now
        resource.last_modified_by = current_rsrc_no
        db.commit()
        db.refresh(resource)
        resource_data = ResourceResponseSchema.model_validate(resource).model_dump(mode="json")
        logger.info(
            f"upload profile picture success for resource: {resource.email} (ID: {resource.id})"
        )
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": resource_data,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading profile picture for resource {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Failed to upload profile picture"},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def remove_profile_picture(rsrc_no: int, db: Session) -> JSONResponse:
    rsrc_no_from_context = get_context("rsrc_no")
    now = get_timezone_now()
    try:
        resource = db.query(Resources).filter(Resources.rsrc_no == rsrc_no, ~Resources.is_archived).first()
        if not resource:
            logger.info("resource not found")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "Resource not found"},
                },
                status_code=status.HTTP_404_NOT_FOUND,
            )

        resource.profile_image_url = None
        resource.last_modified_at = now
        resource.last_modified_by = rsrc_no_from_context
        db.commit()
        db.refresh(resource)
        resource_data = ResourceResponseSchema.model_validate(resource).model_dump(mode="json")
        logger.info(
            f"remove profile picture success for resource: {resource.email} (ID: {resource.id})"
        )
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": resource_data,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing profile picture for resource {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Failed to remove profile picture"},
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


async def change_password(schema: PasswordChangeSchema, rsrc_no: int, db: Session) -> JSONResponse:
    current_rsrc_no = get_context("rsrc_no")
    now = get_timezone_now()
    try:
        if schema.rsrc_no != rsrc_no:
            logger.info("change password attempt failed - resource id mismatch")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_403_FORBIDDEN,
                    "success": False,
                    "result": {"message": "You can only change your own password"},
                },
                status_code=status.HTTP_200_OK,
            )

        resource = db.query(Resources).filter(Resources.rsrc_no == schema.rsrc_no, ~Resources.is_archived).first()
        if not resource:
            logger.info(f"resource not found for resource")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "success": False,
                    "result": {"message": "Resource not found"},
                },
                status_code=status.HTTP_200_OK,
            )
        
        if not verify_password(schema.old_password, resource.login_password):
            logger.info(f"old password is incorrect for resource")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "success": False,
                    "result": {"message": "Old password is incorrect"},
                },
                status_code=status.HTTP_200_OK,
            )
        
        resource.login_password = hash_password(schema.new_password)
        resource.require_password_change = False
        resource.last_modified_at = now
        resource.last_modified_by = current_rsrc_no
        db.commit()
        logger.info(
            f"change password success for resource: {resource.email} (ID: {resource.rsrc_no})"
        )
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": {"message": "Password changed successfully"},
            },
            status_code=status.HTTP_200_OK,
        )
 
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password for resource {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Error changing password"},
            },
            status_code=status.HTTP_200_OK,
        )


async def assignee_users_list(db: Session) -> JSONResponse:
    
    try:
        list_of_resources = db.query(Resources).filter(Resources.is_archived == False, Resources.is_active == True).all()
        list_of_resources_data = [
            ResourceResponseSchema.model_validate(resource).model_dump(mode="json")
            for resource in list_of_resources
        ]
        logger.info(f"Get list of resources success for {len(list_of_resources_data)} resources")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": list_of_resources_data,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error(f"Error getting list of resources: {str(e)}")  
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": [],
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )