from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from jose import jwt
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import config
from src.core.logger import logger
from src.core.context import set_context
from src.core.database import get_db
from src.core.timezone_utils import get_timezone_now
security = HTTPBearer()


def create_forget_password_token(data: dict, expiration_delta: int = None):

    try:            
        if not data.get('rsrc_no'):
            logger.error(f"Resource rsrc_no is required for creating forget password token")
            return None
        to_encode = data.copy()
        expiration_time = datetime.now() + timedelta(seconds=expiration_delta or config.EMAIL_EXPIRATION_DELTA)
        to_encode.update({'expire': str(expiration_time.isoformat())})
        forget_password_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        logger.info(f"Forget password token created for resource: {data.get('rsrc_no')}")
        return forget_password_token
    except Exception as e:
        logger.error(f"Error creating forget password token: {str(e)}")
        return None

def verify_token(token: str):  
    from src.resources.models import Resources
    try:
        decoded_data = decode_token(token)
    
        if datetime.now() > datetime.fromisoformat(decoded_data.get('expire')):
            logger.warning(f"Token expired")
            raise HTTPException(detail="token expired", status_code=status.HTTP_403_FORBIDDEN)
        logger.info(f"Token verified for resource: {decoded_data.get('rsrc_no')}")
        if not Resources.get(decoded_data.get('rsrc_no')):
            raise HTTPException(detail="resource not found", status_code=status.HTTP_401_UNAUTHORIZED)
        logger.info(f"Resource found: {decoded_data.get('rsrc_no')}")
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None
    return decoded_data


def create_tokens(data: dict, token_type: str = 'access') -> dict:
    to_encode = data.copy()
    
    if token_type == 'access':
        expires_delta = timedelta(seconds=config.ACCESS_TOKEN_EXPIRATION_TIME)
    else:
        expires_delta = timedelta(seconds=config.REFRESH_TOKEN_EXPIRATION_TIME)
    
    utc_now = datetime.now(ZoneInfo("UTC"))
    expire = utc_now + expires_delta
    to_encode.update({
        'exp': expire,
        'type': token_type,
        'iat': utc_now
    })
    
    token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    logger.info(f"Token created for resource: {data.get('rsrc_no')}")
    return {
        'token': token,
        'expires': expire.isoformat()
    }

def create_access_token(data: dict) -> dict:
    try:
        access_token = create_tokens(data, 'access')
        refresh_token = create_tokens(data, 'refresh')

        return {
            'access_token': access_token['token'],
            'refresh_token': refresh_token['token'],
            'token_type': 'bearer',
            'expires_in': config.ACCESS_TOKEN_EXPIRATION_TIME,
            'entered_by': data.get('entered_by')
        }
    except Exception as e:
        logger.error(f"Error creating access token({data.get('rsrc_no')}): {str(e)}")
        return None

def decode_token(token: str, token_type: str = None):
    
    try:
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
            options={"require_exp": True}
        )
        if token_type and payload.get('type') != token_type:
            logger.warning(f"Invalid token type. Expected.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}"
            )
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token has expired")
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

    try:
        from src.resources.models import Resources
        set_context(db=db)
        decoded_data = decode_token(credentials.credentials)
        rsrc_no = decoded_data.get('rsrc_no')
        rsrc = db.query(Resources).filter(Resources.rsrc_no == rsrc_no).first()
        
        if not rsrc:
            logger.warning(f"Resource not found with rsrc_no: {rsrc_no}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Resource not found"
            )
            
        if getattr(rsrc, 'require_password_change', False):
            logger.info(f"Password change required for resource: {rsrc.rsrc_no}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required"
            )
        
        set_context(login_name=rsrc.email)
        set_context(rsrc_no=rsrc.rsrc_no)
        set_context(rsrc_id=rsrc.id)
        set_context(rsrc_type=rsrc.rsrc_type)
        
        decoded_data.pop('exp', None) 
        decoded_data.pop('type', None)
        decoded_data.pop('iat', None)
        
        return decoded_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user({rsrc.rsrc_no}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not validate credentials"
        )