from datetime import datetime

from fastapi.exceptions import HTTPException
from fastapi import status
from pydantic import EmailStr

from src.auth.schema import LoginCredentialSchema
from src.users.models import Users
from src.users.utils import verify_password
from src.core.logger import logger
from src.auth.utils import create_access_token, decode_token
from src.core.config import config


async def login_user(data: LoginCredentialSchema):
    """
    Login User API
    """
    logger.info(f'Checking credentials for user login: {data.LoginName}')
    user = Users.fetch_records({"LoginName": data.LoginName})
    if user and verify_password(data.LoginPassword, user[0].LoginPassword):
        return create_access_token({
            'LoginName': user[0].LoginName,
            'id': user[0].id
        })
    else:
        raise HTTPException(detail="Unable to validate credentials", status_code=status.HTTP_401_UNAUTHORIZED)


async def refresh_token(refresh_token: str):
    decoded_data = decode_token(refresh_token)

    if datetime.now() > datetime.fromisoformat(decoded_data.get('expire')):
        raise HTTPException(detail="token expired", status_code=status.HTTP_403_FORBIDDEN)
    
    return create_access_token(decoded_data)


