from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from jose import jwt, JWTError

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import config
from src.core.logger import logger
from src.users.models import Users
from src.core.context import set_context
from src.core.database import get_db

# In-memory set to store blacklisted tokens (for local development only)
_blacklisted_tokens: Set[str] = set()

security = HTTPBearer()



def create_forget_password_token(data: dict, expiration_delta: int = None):
    """
    Creating forget password token
    """
    to_encode = data.copy()
    expiration_time = datetime.now() + timedelta(seconds=expiration_delta or config.EMAIL_EXPIRATION_DELTA)
    to_encode.update({'expire': str(expiration_time.isoformat())})
    forget_password_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return forget_password_token

def verify_token(token: str):
    """
    Verify Token
    """
    decoded_data = decode_token(token)
 
    if datetime.now() > datetime.fromisoformat(decoded_data.get('expire')):
        raise HTTPException(detail="token expired", status_code=status.HTTP_403_FORBIDDEN)
    
    if not Users.get(decoded_data.get('id')):
        raise HTTPException(detail="user not found", status_code=status.HTTP_401_UNAUTHORIZED)
    
    return decoded_data


def create_tokens(data: dict, token_type: str = 'access') -> dict:
    """
    Create access or refresh token
    :param data: Dictionary containing user data
    :param token_type: Type of token to create ('access' or 'refresh')
    :return: Dictionary containing the token and its expiration time
    """
    to_encode = data.copy()
    
    if token_type == 'access':
        expires_delta = timedelta(seconds=config.ACCESS_TOKEN_EXPIRATION_TIME)
    else:  # refresh token
        expires_delta = timedelta(seconds=config.REFRESH_TOKEN_EXPIRATION_TIME)
    
    expire = datetime.now() + expires_delta
    to_encode.update({
        'exp': expire,
        'type': token_type,
        'iat': datetime.now()
    })
    
    token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return {
        'token': token,
        'expires': expire.isoformat()
    }

def create_access_token(data: dict) -> dict:
    """
    Create both access and refresh tokens
    :param data: Dictionary containing user data
    :return: Dictionary with access_token and refresh_token
    """
    access_token = create_tokens(data, 'access')
    refresh_token = create_tokens(data, 'refresh')
    
    return {
        'access_token': access_token['token'],
        'refresh_token': refresh_token['token'],
        'token_type': 'bearer',
        'expires_in': config.ACCESS_TOKEN_EXPIRATION_TIME,
        'entered_by': data.get('entered_by')
    }

def decode_token(token: str, token_type: str = None):
    try:
        # Decode the token
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
            options={"require_exp": True}
        )
        
        # Verify token type if specified
        if token_type and payload.get('type') != token_type:
            logger.warning(f"Invalid token type. Expected {token_type}, got {payload.get('type')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}"
            )
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTClaimsError as e:
        logger.warning(f"Token claims error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims"
        )
    except jwt.JWTError as e:
        logger.warning(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing token"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    Get Current Authenticated User
    
    Args:
        credentials: HTTP Authorization credentials containing the JWT token
        db: Database session
        
    Returns:
        dict: Decoded token data with user information
        
    Raises:
        HTTPException: If token is invalid, expired, or user not found
    """
    try:
        # Decode the token (this validates the signature and expiration)
        decoded_data = decode_token(credentials.credentials)
        
        # Get user from database
        user = Users.get(decoded_data.get('id'))
        if not user:
            logger.warning(f"User not found with ID: {decoded_data.get('id')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        # Check if password change is required
        if getattr(user, 'require_password_change', False):
            logger.info(f"Password change required for user: {user.login_name}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required"
            )
        
        # Set context for logging and auditing
        set_context(login_name=user.login_name)
        set_context(user_id=user.id)
        set_context(entered_by=user.entered_by)
        set_context(db=db)
        
        # Clean up token data before returning
        decoded_data.pop('exp', None)  # Remove JWT expiration timestamp
        decoded_data.pop('type', None)  # Remove token type
        
        return decoded_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not validate credentials"
        )
    return decoded_data