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
from src.auth.schema import PasswordResetSchema, PasswordChangeSchema, LogoutResponseSchema
from src.users.models import Users
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


async def login_user(data: LoginCredentialSchema):
    try:
        logger.info(f'Login attempt for user: {data.login_name}')
        
        # Find user by login name
        users = Users.fetch_records({"login_name": data.login_name})
        if not users:
            logger.warning(f'User not found: {data.login_name}')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        user_obj = users[0]
        
        # Verify password
        if not verify_password(data.login_password, user_obj.login_password):
            logger.warning(f'Invalid password for user: {data.login_name}')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create tokens
        token_data = create_access_token({
            'login_name': user_obj.login_name,
            'id': user_obj.id,
            'entered_by': getattr(user_obj, 'entered_by', None)
        })
        
        # Prepare user response
        user_response = {   
            'id': user_obj.id,
            'full_name': user_obj.full_name or '',
            'email': user_obj.email or '',
            'login_name': user_obj.login_name or '',
            'require_password_change': bool(getattr(user_obj, 'require_password_change', False)),
            'entered_by': getattr(user_obj, 'entered_by', None),
            'last_modified_by': getattr(user_obj, 'last_modified_by', None)
        }
        
        # Add user object to the response
        response = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'token_type': 'bearer',
            'expires_in': config.ACCESS_TOKEN_EXPIRATION_TIME,
            'user': user_response
        }
        
        logger.info(f'User {user_obj.login_name} logged in successfully')
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Login error for user {data.login_name}: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )


async def refresh_token(refresh_token: str):
    """
    Refresh access token using a valid refresh token
    """
    try:
        # Decode the refresh token
        payload = decode_token(refresh_token)
        
        # Check if the token is a refresh token
        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
            
        # Check if user still exists
        user = Users.get(payload.get('id'))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        # Create new tokens
        token_data = {
            'login_name': user.login_name,
            'id': user.id,
            'entered_by': getattr(user, 'entered_by', None)
        }
        
        return create_access_token(token_data)
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not refresh token"
        )


async def forget_password(email: EmailStr):
    """
    Forget Password API
    """
    try:
        users = Users.fetch_records({"email": email})
 
        if users:
            user = users[0]
            token = create_forget_password_token(
                {"email": user.email, "id": user.id}
            )
            password_reset_link = f"{config.FRONTEND_URL}reset-password?token={token}"
            send_email(
                receiver_email=user.email,
                subject="Password Reset Request",
                template_name="forget_password.html",
                context={"full_name": user.full_name, "reset_link": password_reset_link}
            )
 
            return {"message": "Password reset link has been sent to your email", "success": True}
    except Exception as e:
        logger.error(f"Error in forget password process: {str(e)}")
        raise HTTPException(detail="Error processing forget password request", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 
async def reset_password(
    schema: PasswordResetSchema
):
    """
    Reset Password API
    """
    try:
        decoded_data = verify_token(schema.token)
        user = Users.get(decoded_data.get('id'))
        
        user.login_password = hash_password(schema.new_password)
        user.require_password_change = False
        user.save()
 
        return {"message": "Password reset successfully", "success": True}
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(detail="Invalid or expired token", status_code=status.HTTP_403_FORBIDDEN)
    
 
async def change_password(
    schema: PasswordChangeSchema
):
    """
    Change Password API
    """
    try:
        user = Users.get(schema.user_id)
 
        if not user:
            raise HTTPException(detail="User not found", status_code=status.HTTP_404_NOT_FOUND)
        
        if not verify_password(schema.old_password, user.login_password):
            raise HTTPException(detail="Old password is incorrect", status_code=status.HTTP_400_BAD_REQUEST)
        
        user.login_password = hash_password(schema.new_password)
        user.require_password_change = False
        user.save()
 
        return {"message": "Password changed successfully", "success": True}
 
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(detail="Error changing password", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 
