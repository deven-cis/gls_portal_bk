import hashlib
import hmac
from typing import Union


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
    elif isinstance(hashed_password, str):
        # Some drivers may return hex strings instead of bytes.
        hashed_password = bytes.fromhex(hashed_password)

    computed_hash = hashlib.sha512(plain_password.encode("utf-8")).digest()
    return hmac.compare_digest(computed_hash, hashed_password)