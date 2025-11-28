from pydantic import BaseModel, EmailStr


class LoginCredentialSchema(BaseModel):
    """
    Login Credential Schema
    """
    LoginName: EmailStr
    LoginPassword: str

class TokenResponseSchema(BaseModel):
    """
    Token Response Schema
    """
    access_token: str
    refresh_token: str
