from datetime import datetime

from fastapi.exceptions import HTTPException
from fastapi import status
from jose import JWTError
from src.auth.schema import LoginCredentialSchema
from src.resources.models import Resources
from src.resources.utils import verify_password
from src.core.logger import logger
from src.auth.utils import create_access_token, decode_token
from pydantic import EmailStr
from src.core.utils import send_email
from src.core.config import config
from src.auth.utils import create_forget_password_token, verify_token
from src.resources.utils import hash_password
from src.auth.schema import PasswordResetSchema, RefreshTokenSchema
from fastapi import Depends
from fastapi.responses import JSONResponse


async def login_user(data: LoginCredentialSchema):
    try:
        logger.info(f"Login attempt for resource: {data.login_name}")
        
        resources = Resources.fetch_records({"email": data.login_name})
        if not resources:
            logger.warning(f"Login failed - resource not found: {data.login_name}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Wrong Email Address"},
                },
                status_code=status.HTTP_200_OK,
            )
            
        rsrc_obj = resources[0]
        
        if not verify_password(data.login_password, rsrc_obj.login_password):
            logger.warning(f"Login failed - invalid password for resource: {data.login_name}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Invalid password"},
                },
                status_code=status.HTTP_200_OK,
            )
        
        token_data = create_access_token({
            'login_name': rsrc_obj.email,
            'rsrc_no': rsrc_obj.rsrc_no,
            'entered_by': getattr(rsrc_obj, 'entered_by', None)
        })
        
        resource_response = {   
            'rsrc_no': rsrc_obj.rsrc_no,
            'full_name': rsrc_obj.full_name or '',
            'email': rsrc_obj.email or '',
            'login_name': rsrc_obj.login_name or '',
            'require_password_change': bool(getattr(rsrc_obj, 'require_password_change', False)),
            'entered_by': getattr(rsrc_obj, 'entered_by', None),
            'last_modified_by': getattr(rsrc_obj, 'last_modified_by', None)
        }
        
        response = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'token_type': 'bearer',
            'expires_in': config.ACCESS_TOKEN_EXPIRATION_TIME,
            'resource': resource_response
        }
        
        logger.info(f"Login successful for resource: {data.login_name} (rsrc_no: {rsrc_obj.rsrc_no})")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": response
            },
            status_code=status.HTTP_200_OK,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Login error for resource {data.login_name}: {str(e)}')
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "An error occurred during login"},
            },
            status_code=status.HTTP_200_OK,
        )

async def refresh_token(data: RefreshTokenSchema):
    try:
        payload = decode_token(data.refresh_token)
        
        if payload.get('type') != 'refresh':
            logger.warning("Token refresh failed - invalid token type")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Invalid token type"}
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
            
        rsrc = Resources.get(payload.get('rsrc_no'))
        if not rsrc:
            logger.warning(f"Token refresh failed - resource not found (rsrc_no: {payload.get('rsrc_no')})")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Resource not found"}
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
            
        token_data = {
            'login_name': rsrc.email,
            'rsrc_no': rsrc.rsrc_no,
            'entered_by': getattr(rsrc, 'entered_by', None)
        }
        
        new_tokens = create_access_token(token_data)
        
        resource_response = {   
            'rsrc_no': rsrc.rsrc_no,
            'full_name': rsrc.full_name or '',
            'email': rsrc.email or '',
            'login_name': rsrc.login_name or '',
            'require_password_change': bool(getattr(rsrc, 'require_password_change', False)),
            'entered_by': getattr(rsrc, 'entered_by', None),
            'last_modified_by': getattr(rsrc, 'last_modified_by', None)
        }
        
        response = {
            'access_token': new_tokens['access_token'],
            'refresh_token': new_tokens['refresh_token'],
            'token_type': 'bearer',
            'expires_in': new_tokens['expires_in'],
            'resource': resource_response
        }
        
        logger.info(f"Token refreshed successfully for resource: {rsrc.email} (rsrc_no: {rsrc.rsrc_no})")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "success": True,
                "result": response
            },
            status_code=status.HTTP_200_OK
        )
        
    except HTTPException as e:
        logger.error(f"HTTPException during token refresh: {e.detail}")
        return JSONResponse(
            content={
                "status_code": e.status_code,
                "success": False,
                "result": {"message": e.detail}
            },
            status_code=e.status_code
        )
    except JWTError as e:
        logger.error(f"JWT error refreshing token: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "success": False,
                "result": {"message": "Invalid token"}
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "success": False,
                "result": {"message": "Could not refresh token"}
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def forget_password(email: EmailStr):
    try:
        logger.info(f"Password reset request for email: {email}")
        resources = Resources.fetch_records({"email": email})
 
        if resources:
            rsrc = resources[0]
            logger.info(f"Password reset link generation for resource: {rsrc.email} (rsrc_no: {rsrc.rsrc_no})")
            token = create_forget_password_token(
                {"email": rsrc.email, "rsrc_no": rsrc.rsrc_no}
            )
            if not token:
                logger.error(f"Error creating forget password token for resource: {rsrc.email} (rsrc_no: {rsrc.rsrc_no})")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "success": False,
                        "result": {"message": "Error creating forget password token"}
                    },
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            password_reset_link = f"{config.FRONTEND_URL}reset-password?token={token}"
            logger.info(f"Password reset link generated for resource: {rsrc.email} (rsrc_no: {rsrc.rsrc_no})")
            send_email(
                receiver_email=rsrc.email,
                subject="Password Reset Request",
                template_name="forget_password.html",
                context={"full_name": rsrc.full_name, "reset_link": password_reset_link}
            )
            logger.info(f"Password reset email sent successfully to: {email}")
 
            return {"message": "Password reset link has been sent to your email", "success": True}
        else:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return {"message": "Password reset link has been sent to your email", "success": True}
    except Exception as e:
        logger.error(f"Error in forget password process for {email}: {str(e)}")
        raise HTTPException(detail="Error processing forget password request", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 
async def reset_password(
    schema: PasswordResetSchema
):
    try:
        decoded_data = verify_token(schema.token)
        rsrc = Resources.get(decoded_data.get('rsrc_no'))
        
        rsrc.login_password = hash_password(schema.new_password)
        rsrc.require_password_change = False
        rsrc.save()
        
        logger.info(f"Password reset successfully for resource: {rsrc.email} (rsrc_no: {rsrc.rsrc_no})")
 
        return {"message": "Password reset successfully", "success": True}
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(detail="Invalid or expired token", status_code=status.HTTP_403_FORBIDDEN)
    
