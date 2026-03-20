from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    context: Optional[List[str]] = None
    response_time_s: Optional[float] = None


class TrainingDataRequest(BaseModel):
    content: str
    is_fraud: bool


class TrainingResponse(BaseModel):
    success: bool
    message: str
    metrics: Optional[dict] = None
