from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BusinessProfile(BaseModel):
    id: int
    nomination: Optional[str] = None
    nom: Optional[str] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    code_postale: Optional[str] = None
    prefixe: Optional[str] = None
    code_pays: Optional[str] = None
    tel: Optional[str] = None
    act: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PhoneCheckRequest(BaseModel):
    phone: str = Field(..., description="Phone number in E.164 format")
    country: str = Field(..., max_length=3)
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PhoneCheckResponse(BaseModel):
    is_fraud: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = None
    reason: Optional[str] = None
    action: str
    similar_cases: int = 0
    response_time_ms: int
    status: str = Field(..., description="blacklist | business | unknown")
    business: Optional[BusinessProfile] = None


class PhoneReportRequest(BaseModel):
    phone: str
    fraud_type: str
    user_id: str
    description: Optional[str] = None