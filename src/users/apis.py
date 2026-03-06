# from src.core.timezone_utils import get_timezone_now
# from fastapi import status
# from fastapi.responses import JSONResponse
# from fastapi import UploadFile
# from sqlalchemy.orm import Session
# from src.core.context import get_context
# from src.core.file_utils import save_image_file
# from src.core.logger import logger
# from src.Resources.models import Resources
# from src.users.schema import UserResponseSchema
# from src.users.utils import hash_password, verify_password
# from src.auth.schema import PasswordChangeSchema


# async def get_current_user_profile(user_id: int, db: Session) -> JSONResponse:

#     try:
#         resource = db.query(Resources).filter(Resources.id == user_id, ~Resources.is_archived).first()
#         if not resource:
#             logger.info("user not found")
#             return JSONResponse(
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "success": False,
#                     "result": {"message": "User not found"},
#                 },
#                 status_code=status.HTTP_404_NOT_FOUND,
#             )
#         user_data = UserResponseSchema.model_validate(resource).model_dump(mode="json")
#         logger.info(
#             f"get current user profile success for user: {resource.email} (ID: {resource.id})"
#         )
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "success": True,
#                 "result": user_data,
#             },
#             status_code=status.HTTP_200_OK,
#         )
#     except Exception as e:
#         logger.error(f"Error getting current user profile for user {str(e)}")
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "success": False,
#                 "result": {"message": "Failed to get current user profile"},
#             },
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  
#         )

# async def upload_profile_picture(user_id: int, file: UploadFile, db: Session) -> JSONResponse:
#     entered_by = get_context("entered_by")
#     now = get_timezone_now()
#     try:
#         resource = db.query(Resources).filter(Resources.id == user_id, ~Resources.is_archived).first()
#         if not resource:
#             logger.info("user not found")
#             return JSONResponse(
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "success": False,
#                     "result": {"message": "User not found"},
#                 },
#                 status_code=status.HTTP_404_NOT_FOUND,
#             )

#         orig_name, path = await save_image_file(file, "profile_pictures")

#         resource.profile_image_url = path
#         resource.last_modified_at = now
#         resource.last_modified_by = entered_by
#         db.commit()
#         db.refresh(resource)
#         user_data = UserResponseSchema.model_validate(resource).model_dump(mode="json")
#         logger.info(
#             f"upload profile picture success for user: {resource.email} (ID: {resource.id})"
#         )
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "success": True,
#                 "result": user_data,
#             },
#             status_code=status.HTTP_200_OK,
#         )
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error uploading profile picture for user {str(e)}")
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "success": False,
#                 "result": {"message": "Failed to upload profile picture"},
#             },
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         )


# async def remove_profile_picture(user_id: int, db: Session) -> JSONResponse:
#     entered_by = get_context("entered_by")
#     now = get_timezone_now()
#     try:
#         resource = db.query(Resources).filter(Resources.id == user_id, ~Resources.is_archived).first()
#         if not resource:
#             logger.info("user not found")
#             return JSONResponse(
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "success": False,
#                     "result": {"message": "User not found"},
#                 },
#                 status_code=status.HTTP_404_NOT_FOUND,
#             )

#         resource.profile_image_url = None
#         resource.last_modified_at = now
#         resource.last_modified_by = entered_by
#         db.commit()
#         db.refresh(resource)
#         user_data = UserResponseSchema.model_validate(resource).model_dump(mode="json")
#         logger.info(
#             f"remove profile picture success for user: {resource.email} (ID: {resource.id})"
#         )
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "success": True,
#                 "result": user_data,
#             },
#             status_code=status.HTTP_200_OK,
#         )
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error removing profile picture for user {str(e)}")
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "success": False,
#                 "result": {"message": "Failed to remove profile picture"},
#             },
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         )


# async def change_password(schema: PasswordChangeSchema, user_id: int, db: Session) -> JSONResponse:
#     entered_by = get_context("entered_by")
#     now = get_timezone_now()
#     try:
#         if schema.user_id != user_id:
#             logger.info("change password attempt failed - user id mismatch")
#             return JSONResponse(
#                 content={
#                     "status_code": status.HTTP_403_FORBIDDEN,
#                     "success": False,
#                     "result": {"message": "You can only change your own password"},
#                 },
#                 status_code=status.HTTP_200_OK,
#             )

#         resource = db.query(Resources).filter(Resources.id == schema.user_id, ~Resources.is_archived).first()
#         if not resource:
#             logger.info(f"user not found for user")
#             return JSONResponse(
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "success": False,
#                     "result": {"message": "User not found"},
#                 },
#                 status_code=status.HTTP_200_OK,
#             )
        
#         if not verify_password(schema.old_password, resource.login_password):
#             logger.info(f"old password is incorrect for user")
#             return JSONResponse(
#                 content={
#                     "status_code": status.HTTP_400_BAD_REQUEST,
#                     "success": False,
#                     "result": {"message": "Old password is incorrect"},
#                 },
#                 status_code=status.HTTP_200_OK,
#             )
        
#         resource.login_password = hash_password(schema.new_password)
#         resource.require_password_change = False
#         resource.last_modified_at = get_timezone_now()
#         db.commit()
#         logger.info(
#             f"change password success for user: {resource.email} (ID: {resource.id})"
#         )
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "success": True,
#                 "result": {"message": "Password changed successfully"},
#             },
#             status_code=status.HTTP_200_OK,
#         )
 
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error changing password for user {str(e)}")
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "success": False,
#                 "result": {"message": "Error changing password"},
#             },
#             status_code=status.HTTP_200_OK,
#         )


# async def assignee_users_list(db: Session) -> JSONResponse:
    
#     try:
#         list_of_users = db.query(Resources).filter(Resources.is_archived == False).all()
#         list_of_users_data = [
#             UserResponseSchema.model_validate(resource).model_dump(mode="json")
#             for resource in list_of_users
#         ]
#         logger.info(f"Get list of users success for {len(list_of_users_data)} users")
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "success": True,
#                 "result": list_of_users_data,
#             },
#             status_code=status.HTTP_200_OK,
#         )
#     except Exception as e:
#         logger.error(f"Error getting list of users: {str(e)}")  
#         return JSONResponse(
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "success": False,
#                 "result": [],
#             },
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         )
