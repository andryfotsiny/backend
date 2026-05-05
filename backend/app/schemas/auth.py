# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    phone: Optional[str] = None
    name: Optional[str] = None
    country_code: str
    role: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@dyleth.com",
                "password": "Admin@2026"
            }
        }
    }


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    phone: Optional[str] = None
    name: Optional[str] = None
    country_code: str
    role: str
    created_at: datetime
    last_active: Optional[datetime] = None
    total_reports: int = 0
    verified_reports: int = 0

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class DeviceTokenCreate(BaseModel):
    token: str
    platform: str


class AuthError(BaseModel):
    detail: str