"""
RoadPulse AI - User & Authentication Schemas
Pydantic validation models preventing privilege escalation and enforcing password safety.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Unique username")


class UserRegister(UserBase):
    """
    Public registration schema.
    Explicitly does NOT allow specifying privileged roles.
    All public registrations are assigned the 'user' role.
    """
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class UserCreateAdmin(UserBase):
    """
    Admin-only user creation schema.
    Only authenticated administrators can specify 'worker' or 'admin' roles.
    """
    password: str = Field(..., min_length=8)
    role: str = Field(default="user", description="Assigned role: admin, worker, or user")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v_low = v.lower().strip()
        if v_low not in ("admin", "worker", "user"):
            raise ValueError("Role must be one of: 'admin', 'worker', 'user'")
        return v_low


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
