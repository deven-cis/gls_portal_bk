import ast
import hashlib
import hmac
from typing import Union

from src.core.logger import logger
def hash_password(password: str) -> bytes:
    """
    Returns the SHA-512 digest for compatibility with existing DB rows.
    """
    return hashlib.sha512(password.encode("utf-8")).digest()


def verify_password(plain_password: str, hashed_password: Union[bytes, memoryview, str]) -> bool:
    """
    Password Verification using SHA-512 to match legacy DB hashes.
    """
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
        # Stored value is a stringified bytes literal; evaluate back to bytes.
        hashed_password = ast.literal_eval(hashed_password.decode())

    logger.info(f'Hashed password: {hashed_password.hex()}')
    computed_hash = hashlib.sha512(plain_password.encode("utf-8")).digest()
    logger.info(f'Computed hash: {computed_hash.hex()}')
    return hmac.compare_digest(computed_hash, hashed_password)