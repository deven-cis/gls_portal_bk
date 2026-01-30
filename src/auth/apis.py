from datetime import datetime

from fastapi.exceptions import HTTPException
from fastapi import status
from jose import JWTError
from src.auth.schema import LoginCredentialSchema
from src.users.models import Users
from src.users.utils import verify_password
from src.core.logger import logger
from src.auth.utils import create_access_token, decode_token
from pydantic import EmailStr
from src.core.utils import send_email
from src.core.config import config
from src.auth.utils import create_forget_password_token, verify_token
from src.users.utils import hash_password
from src.auth.schema import PasswordResetSchema, RefreshTokenSchema
from src.users.models import Users
from fastapi import Depends
from fastapi.responses import JSONResponse
from src.core.timezone_utils import get_default_timezone, get_timezone_abbreviation


async def login_user(data: LoginCredentialSchema):
    try:
        logger.info(f"Login attempt for user: {data.login_name}")
        
        users = Users.fetch_records({"email": data.login_name})
        if not users:
            logger.warning(f"Login failed - user not found: {data.login_name}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Wrong Email Address"},
                },
                status_code=status.HTTP_200_OK,
            )
            
        user_obj = users[0]
        
        if not verify_password(data.login_password, user_obj.login_password):
            logger.warning(f"Login failed - invalid password for user: {data.login_name}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "Invalid password"},
                },
                status_code=status.HTTP_200_OK,
            )
        
        token_data = create_access_token({
            'login_name': user_obj.email,
            'id': user_obj.id,
            'entered_by': getattr(user_obj, 'entered_by', None)
        })
        
        user_response = {   
            'id': user_obj.id,
            'full_name': user_obj.full_name or '',
            'email': user_obj.email or '',
            'login_name': user_obj.login_name or '',
            'timezone': get_default_timezone(),
            'timezone_abbr': get_timezone_abbreviation()
        }
        
        response = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'token_type': 'bearer',
            'expires_in': config.ACCESS_TOKEN_EXPIRATION_TIME,
            'user': user_response
        }
        
        logger.info(f"Login successful for user: {data.login_name} (ID: {user_obj.id})")
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
        logger.error(f'Login error for user {data.login_name}: {str(e)}')
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
            
        user = Users.get(payload.get('id'))
        if not user:
            logger.warning(f"Token refresh failed - user not found (ID: {payload.get('id')})")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_401_UNAUTHORIZED,
                    "success": False,
                    "result": {"message": "User not found"}
                },
                status_code=status.HTTP_401_UNAUTHORIZED
            )
            
        token_data = {
            'login_name': user.email,
            'id': user.id,
            'entered_by': getattr(user, 'entered_by', None)
        }
        
        new_tokens = create_access_token(token_data)
        
        user_response = {   
            'id': user.id,
            'full_name': user.full_name or '',
            'email': user.email or '',
            'login_name': user.login_name or '',
            'timezone': get_default_timezone(),
            'timezone_abbr': get_timezone_abbreviation()
        }
        
        response = {
            'access_token': new_tokens['access_token'],
            'refresh_token': new_tokens['refresh_token'],
            'token_type': 'bearer',
            'expires_in': new_tokens['expires_in'],
            'user': user_response
        }
        
        logger.info(f"Token refreshed successfully for user: {user.email} (ID: {user.id})")
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
        users = Users.fetch_records({"email": email})
 
        if users:
            user = users[0]
            logger.info(f"Password reset link generation for user: {user.email} (ID: {user.id})")
            token = create_forget_password_token(
                {"email": user.email, "id": user.id}
            )
            if not token:
                logger.error(f"Error creating forget password token for user: {user.email} (ID: {user.id})")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "success": False,
                        "result": {"message": "Error creating forget password token"}
                    },
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            password_reset_link = f"{config.FRONTEND_URL}reset-password?token={token}"
            logger.info(f"Password reset link generated for user: {user.email} (ID: {user.id})")
            send_email(
                receiver_email=user.email,
                subject="Password Reset Request",
                template_name="forget_password.html",
                context={"full_name": user.full_name, "reset_link": password_reset_link}
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
        user = Users.get(decoded_data.get('id'))
        
        user.login_password = hash_password(schema.new_password)
        user.require_password_change = False
        user.save()
        
        logger.info(f"Password reset successfully for user: {user.email} (ID: {user.id})")
 
        return {"message": "Password reset successfully", "success": True}
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(detail="Invalid or expired token", status_code=status.HTTP_403_FORBIDDEN)
    
