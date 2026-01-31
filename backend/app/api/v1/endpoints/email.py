from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.email import EmailAnalyzeRequest, EmailAnalyzeResponse
from app.services.detection import detection_service
from app.services.cache import cache_service

router = APIRouter()

@router.post("/analyze-email", response_model=EmailAnalyzeResponse)
async def analyze_email(
    request: EmailAnalyzeRequest,
    db: AsyncSession = Depends(get_db)
):
    if request.user_id:
        rate_ok = await cache_service.check_rate_limit(request.user_id)
        if not rate_ok:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    result = await detection_service.check_email(
        db=db,
        sender=request.sender,
        subject=request.subject,
        body=request.body,
        user_id=request.user_id
    )
    
    return EmailAnalyzeResponse(**result)
