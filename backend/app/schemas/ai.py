from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    context: Optional[List[str]] = None
