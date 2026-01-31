from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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

class PhoneReportRequest(BaseModel):
    phone: str
    fraud_type: str
    user_id: str
    description: Optional[str] = None
