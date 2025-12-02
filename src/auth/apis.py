from datetime import datetime

from fastapi.exceptions import HTTPException
from fastapi import status
from src.auth.schema import LoginCredentialSchema
from src.users.models import Users
from src.users.utils import verify_password
from src.core.logger import logger
from src.auth.utils import create_access_token, decode_token


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


