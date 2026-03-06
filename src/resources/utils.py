import ast
import hashlib
import hmac
from typing import Union
from src.core.logger import logger

def hash_password(password: str) -> bytes:

    try:
        return hashlib.sha512(password.encode("utf-8")).digest()
    except Exception as e:
        logger.error(f"Error hashing password: {str(e)}")
        return None


def verify_password(plain_password: str, hashed_password: Union[bytes, memoryview, str]) -> bool:
    try:
        if hashed_password is None:
            return False

        if isinstance(hashed_password, memoryview):
            hashed_password = hashed_password.tobytes()

        if isinstance(hashed_password, str):
            hashed_password = bytes.fromhex(hashed_password)
        elif (
            isinstance(hashed_password, bytes)
            and hashed_password.startswith(b"b'")
            and hashed_password.endswith(b"'")
        ):
            hashed_password = ast.literal_eval(hashed_password.decode())

        computed_hash = hashlib.sha512(plain_password.encode("utf-8")).digest()
        result = hmac.compare_digest(computed_hash, hashed_password)
        return result
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False