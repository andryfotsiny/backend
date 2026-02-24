from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    country_code: str
    password: str

class UserResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    phone: Optional[str] = None
    country_code: str
    role: str
    created_at: datetime
    report_count: int

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    country_code: Optional[str] = None
    role: Optional[str] = None  # Uniquement modifiable par l'Admin

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[UUID] = None
