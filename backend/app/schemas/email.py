from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class EmailAnalyzeRequest(BaseModel):
    sender: EmailStr
    subject: str
    body: str = Field(..., max_length=50000)
    headers: Optional[dict] = None
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EmailAnalyzeResponse(BaseModel):
    is_fraud: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    phishing_type: Optional[str] = None
    risk_factors: List[str] = []
    sender_verified: bool
    spf_valid: bool
    dkim_valid: bool
    action: str
    response_time_ms: int

class EmailReportRequest(BaseModel):
    sender: EmailStr
    subject: str
    user_id: str
    fraud_type: str
