from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re

# === REGISTER ===

class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="Email utilisateur")
    password: str = Field(..., min_length=8, max_length=100, description="Mot de passe (min 8 caractères)")
    phone: Optional[str] = Field(None, description="Numéro téléphone (optionnel)")
    country_code: str = Field("FR", max_length=2, description="Code pays")

    @validator('password')
    def validate_password(cls, v):
        """Validation force du mot de passe"""
        if len(v) < 8:
            raise ValueError('Mot de passe trop court (min 8 caractères)')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Mot de passe doit contenir au moins une majuscule')
        if not re.search(r'[a-z]', v):
            raise ValueError('Mot de passe doit contenir au moins une minuscule')
        if not re.search(r'[0-9]', v):
            raise ValueError('Mot de passe doit contenir au moins un chiffre')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        """Validation format téléphone"""
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Format téléphone invalide (utiliser E.164: +33612345678)')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "phone": "+33612345678",
                "country_code": "FR"
            }
        }


# === LOGIN ===

class UserLogin(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }


# === TOKEN ===

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Expiration en secondes")


class TokenPayload(BaseModel):
    sub: str  # user_id
    exp: int  # expiration timestamp
    type: str = "access"  # access ou refresh


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# === USER RESPONSE ===

class UserResponse(BaseModel):
    id: str
    email: str
    phone: Optional[str]
    country_code: str
    created_at: datetime
    last_active: datetime
    total_reports: int = 0
    verified_reports: int = 0

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    id: str
    email: str
    phone: Optional[str]
    country_code: str
    settings: dict
    created_at: datetime
    last_active: datetime
    stats: dict = {}

    class Config:
        from_attributes = True


# === UPDATE PROFILE ===

class UserUpdate(BaseModel):
    phone: Optional[str] = None
    country_code: Optional[str] = None
    settings: Optional[dict] = None

    @validator('settings')
    def validate_settings(cls, v):
        """Valider structure settings"""
        if v:
            allowed_keys = ['notifications', 'language', 'theme', 'auto_block']
            for key in v.keys():
                if key not in allowed_keys:
                    raise ValueError(f'Clé settings invalide: {key}')
        return v


# === PASSWORD CHANGE ===

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Nouveau mot de passe trop court')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Doit contenir une majuscule')
        if not re.search(r'[a-z]', v):
            raise ValueError('Doit contenir une minuscule')
        if not re.search(r'[0-9]', v):
            raise ValueError('Doit contenir un chiffre')
        return v


# === DEVICE TOKEN (pour notifications push) ===

class DeviceTokenCreate(BaseModel):
    token: str = Field(..., description="Token FCM/APNS")
    platform: str = Field(..., description="android ou ios")

    @validator('platform')
    def validate_platform(cls, v):
        if v not in ['android', 'ios']:
            raise ValueError('Platform doit être android ou ios')
        return v


# === AUTH ERROR RESPONSES ===

class AuthError(BaseModel):
    detail: str
    error_code: str

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Email ou mot de passe incorrect",
                "error_code": "INVALID_CREDENTIALS"
            }
        }