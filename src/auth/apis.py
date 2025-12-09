from datetime import datetime

from fastapi.exceptions import HTTPException
from fastapi import status
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
from src.auth.utils import add_to_blacklist, is_token_blacklisted


async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """
    Logout User API
    """
    token = credentials.credentials
    
    # Add the token to the blacklist
    add_to_blacklist(token)
    
    logger.info(f"User logged out. Token blacklisted.")
    
    return {
        "message": "Successfully logged out. The token has been invalidated.",
        "success": True
    }


async def login_user(data: LoginCredentialSchema):
    """
    Login User API
    """
    logger.info(f'Checking credentials for user login: {data.login_name}')
    logger.info(f'Checking credentials for user password: {data.login_password}')
    user = Users.fetch_records({"login_name": data.login_name})
    if user and verify_password(data.login_password, user[0].login_password):
        return create_access_token({
            'login_name': user[0].login_name,
            'id': user[0].id
        })  
    else:
        raise HTTPException(detail="Unable to validate credentials", status_code=status.HTTP_401_UNAUTHORIZED)


async def refresh_token(refresh_token: str):
    decoded_data = decode_token(refresh_token)

    if datetime.now() > datetime.fromisoformat(decoded_data.get('expire')):
        raise HTTPException(detail="token expired", status_code=status.HTTP_403_FORBIDDEN)
    
    return create_access_token(decoded_data)


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
 
 
