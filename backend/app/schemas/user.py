from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    country_code: str
    password: str

class UserResponse(BaseModel):
    user_id: str
    email_hash: str
    country_code: str
    created_at: datetime
    report_count: int

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None
