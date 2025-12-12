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


def add_to_blacklist(token: str):
    """Add a token to the blacklist"""
    _blacklisted_tokens.add(token)


def is_token_blacklisted(token: str) -> bool:
    """Check if a token is blacklisted"""
    return token in _blacklisted_tokens


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


def create_access_token(data: dict, expiration_delta: int = None):
    """
    Creating access token
    """
    to_encode = data.copy()
    expiration_time = datetime.now() + timedelta(seconds=expiration_delta or config.ACCESS_TOKEN_EXPIRATION_TIME)
    to_encode.update({'expire': str(expiration_time.isoformat())})
    access_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    refresh_expiration = datetime.now() + timedelta(seconds=expiration_delta or config.REFRESH_TOKEN_EXPIRATION_TIME)
    to_encode['expire'] = str(refresh_expiration.isoformat())
    refresh_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'entered_by': data.get('entered_by')
    }

def decode_token(token: str):
    """
    Token decode
    """
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Failed to decode token: {str(e)}")
        raise HTTPException(
            detail='Could not validate credentials',
            status_code=status.HTTP_401_UNAUTHORIZED
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    Get Current Authenticated User
    """
    decoded_data = decode_token(credentials.credentials)

    if datetime.now() > datetime.fromisoformat(decoded_data.get('expire')):
        raise HTTPException(detail="token expired", status_code=status.HTTP_403_FORBIDDEN)
    
    user = Users.get(decoded_data.get('id'))
    if not user:
        raise HTTPException(detail="user not found", status_code=status.HTTP_401_UNAUTHORIZED)
        
    if user.require_password_change:
        raise HTTPException(
            detail="Password change required",
            status_code=status.HTTP_403_FORBIDDEN
        )    
    
    set_context(login_name=user.login_name)
    set_context(user_id=user.id)
    set_context(entered_by=user.entered_by)
    set_context(db=db)
    
    decoded_data.pop('expire')
    return decoded_data