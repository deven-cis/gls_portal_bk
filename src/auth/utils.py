from datetime import datetime, timedelta
from jose import jwt, JWTError

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import config
from src.core.logger import logger
from src.users.models import Users
from src.core.context import set_context
from src.core.database import get_db


security = HTTPBearer()


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
        'refresh_token': refresh_token
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
    set_context(login_name=user.login_name)
    set_context(user_id=user.id)
    set_context(entered_by=user.entered_by)
    set_context(db=db)
    
    decoded_data.pop('expire')
    return decoded_data