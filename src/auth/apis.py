from datetime import datetime
from threading import Lock

from fastapi.exceptions import HTTPException
from fastapi import status, Depends
from jose import JWTError
from sqlalchemy.orm import Session

from src.auth.schema import LoginCredentialSchema
from src.resources.utils import verify_password
from src.core.logger import logger
from src.auth.utils import create_access_token, decode_token
from pydantic import EmailStr
from src.core.utils import send_email
from src.core.config import config
from src.auth.utils import create_forget_password_token, verify_token
from src.resources.utils import hash_password
from src.auth.schema import PasswordResetSchema, RefreshTokenSchema
from fastapi.responses import JSONResponse
from src.core.database import get_db

# Global lock to prevent concurrent token refresh per user
_refresh_locks = {}
_locks_lock = Lock()

def get_user_refresh_lock(rsrc_no: int):
    """Get or create a lock for a specific user"""
    with _locks_lock:
        if rsrc_no not in _refresh_locks:
            _refresh_locks[rsrc_no] = Lock()
        return _refresh_locks[rsrc_no]


async def login_user(data: LoginCredentialSchema):
    try:
        # Lazy import to prevent circular import
        from src.resources.models import Resources
        
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
        rsrc_name = rsrc_obj.full_name if rsrc_obj.full_name else (rsrc_obj.first_name or rsrc_obj.email)
        token_data = create_access_token({
            'login_name': rsrc_obj.email,
            'rsrc_no': rsrc_obj.rsrc_no,
            'rsrc_name': rsrc_name,
            'rsrc_role': rsrc_obj.priority_level,
        })
        
        response = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
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

async def refresh_token(data: RefreshTokenSchema, db: Session = Depends(get_db)):
    try:
        from src.resources.models import Resources
        
        payload = decode_token(data.refresh_token)
        rsrc_no = payload.get('rsrc_no')
        
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
        
        # Get user-specific lock to prevent concurrent refreshes
        user_lock = get_user_refresh_lock(rsrc_no)
        if not user_lock.acquire(blocking=False):
            logger.warning(f"Token refresh already in progress for rsrc_no: {rsrc_no}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                    "success": False,
                    "result": {"message": "Token refresh already in progress"}
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        try:
            # Query by rsrc_no field (not id)
            rsrc_obj = db.query(Resources).filter(Resources.rsrc_no == rsrc_no).first()
            
            if not rsrc_obj:
                logger.warning(f"Token refresh failed - resource not found (rsrc_no: {rsrc_no})")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_401_UNAUTHORIZED,
                        "success": False,
                        "result": {"message": "Resource not found"}
                    },
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if resource is active
            if not rsrc_obj.is_active:
                logger.warning(f"Token refresh failed - resource inactive (rsrc_no: {rsrc_no})")
                return JSONResponse(
                    content={
                        "status_code": status.HTTP_401_UNAUTHORIZED,
                        "success": False,
                        "result": {"message": "Resource is inactive"}
                    },
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            
            rsrc_name = rsrc_obj.full_name if rsrc_obj.full_name else (rsrc_obj.first_name or rsrc_obj.email)
            token_data = {
                'login_name': rsrc_obj.email,
                'rsrc_no': rsrc_obj.rsrc_no,
                'rsrc_name': rsrc_name,
                'rsrc_role': rsrc_obj.priority_level
            }
            
            new_tokens = create_access_token(token_data)
            
            response = {
                'access_token': new_tokens['access_token'],
                'refresh_token': new_tokens['refresh_token'],
            }
            
            logger.info(f"Token refreshed successfully for resource: {rsrc_obj.email} (rsrc_no: {rsrc_obj.rsrc_no})")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_200_OK,
                    "success": True,
                    "result": response
                },
                status_code=status.HTTP_200_OK
            )
        finally:
            user_lock.release()
        
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
        # Lazy import to prevent circular import
        from src.resources.models import Resources
        
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
        # Lazy import to prevent circular import
        from src.resources.models import Resources
        
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
    
