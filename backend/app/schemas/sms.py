from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class SMSAnalyzeRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    sender: str
    user_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SMSAnalyzeResponse(BaseModel):
    is_fraud: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = None
    risk_factors: List[str] = []
    action: str
    similar_frauds: int = 0
    response_time_ms: int

class SMSReportRequest(BaseModel):
    content: str
    sender: str
    user_id: str
    fraud_type: str
