from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.sms import SMSAnalyzeRequest, SMSAnalyzeResponse
from app.services.detection import detection_service
from app.services.cache import cache_service

router = APIRouter()


@router.post("/analyze-sms", response_model=SMSAnalyzeResponse)
async def analyze_sms(request: SMSAnalyzeRequest, db: AsyncSession = Depends(get_db)):
    if request.user_id:
        rate_ok = await cache_service.check_rate_limit(request.user_id)
        if not rate_ok:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    result = await detection_service.check_sms(
        db=db, content=request.content, sender=request.sender, user_id=request.user_id
    )

    return SMSAnalyzeResponse(**result)
