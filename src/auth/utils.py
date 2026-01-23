from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import config
from src.core.logger import logger
from src.core.context import set_context
from src.core.database import get_db
security = HTTPBearer()


def create_forget_password_token(data: dict, expiration_delta: int = None):

    try:            
        logger.info(f"Creating forget password token for user: {data.get('id')}")
        if not data.get('id'):
            logger.error(f"User ID is required for creating forget password token")
            return None
        to_encode = data.copy()
        expiration_time = datetime.now() + timedelta(seconds=expiration_delta or config.EMAIL_EXPIRATION_DELTA)
        to_encode.update({'expire': str(expiration_time.isoformat())})
        forget_password_token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
        logger.info(f"Forget password token created for user: {data.get('id')}")
        return forget_password_token
    except Exception as e:
        logger.error(f"Error creating forget password token: {str(e)}")
        return None

def verify_token(token: str):  
    from src.users.models import Users
    logger.info(f"Verifying token")
    try:
        decoded_data = decode_token(token)
    
        if datetime.now() > datetime.fromisoformat(decoded_data.get('expire')):
            logger.warning(f"Token expired")
            raise HTTPException(detail="token expired", status_code=status.HTTP_403_FORBIDDEN)
        logger.info(f"Token verified for user: {decoded_data.get('id')}")
        if not Users.get(decoded_data.get('id')):
            raise HTTPException(detail="user not found", status_code=status.HTTP_401_UNAUTHORIZED)
        logger.info(f"User found: {decoded_data.get('id')}")
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None
    return decoded_data


def create_tokens(data: dict, token_type: str = 'access') -> dict:
    to_encode = data.copy()
    
    if token_type == 'access':
        logger.info(f"Creating access token for user: {data.get('id')}")
        expires_delta = timedelta(seconds=config.ACCESS_TOKEN_EXPIRATION_TIME)
    else:
        expires_delta = timedelta(seconds=config.REFRESH_TOKEN_EXPIRATION_TIME)
    
    expire = datetime.utcnow() + expires_delta
    logger.info(f"Expire: {expire}")
    to_encode.update({
        'exp': expire,
        'type': token_type,
        'iat': datetime.utcnow()
    })
    
    token = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    logger.info(f"Token created for user: {data.get('id')}")
    return {
        'token': token,
        'expires': expire.isoformat()
    }

def create_access_token(data: dict) -> dict:
    try:
        logger.info(f"Creating access token for user: {data.get('id')}")
        access_token = create_tokens(data, 'access')
        refresh_token = create_tokens(data, 'refresh')
        logger.info(f"Access token created for user: {data.get('id')}")
        logger.info(f"Refresh token created for user: {data.get('id')}")

        return {
            'access_token': access_token['token'],
            'refresh_token': refresh_token['token'],
            'token_type': 'bearer',
            'expires_in': config.ACCESS_TOKEN_EXPIRATION_TIME,
            'entered_by': data.get('entered_by')
        }
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
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
            logger.warning(f"Invalid token type. Expected {token_type}, got {payload.get('type')}")
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
        from src.users.models import Users
        set_context(db=db)
        decoded_data = decode_token(credentials.credentials)
        user_id = decoded_data.get('id')
        user = db.query(Users).filter(Users.id == user_id).first()
        
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        if getattr(user, 'require_password_change', False):
            logger.info(f"Password change required for user: {user.login_name} (ID: {user.id})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required"
            )
        
        set_context(login_name=user.login_name)
        set_context(user_id=user.id)
        set_context(entered_by=user.user_no)
        
        decoded_data.pop('exp', None) 
        decoded_data.pop('type', None)
        decoded_data.pop('iat', None)
        
        logger.info(f"Current user authenticated: {user.login_name} (ID: {user.id})")
        return decoded_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not validate credentials"
        )