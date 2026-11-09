"""
RoadPulse AI - Token Schemas
JWT authentication response models.
"""

from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_seconds: Optional[int] = None


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int
    iat: Optional[int] = None
