from fastapi import APIRouter
from app.api.v1.endpoints import phone, sms, email, reports,auth,analytics

api_router = APIRouter()

api_router.include_router(phone.router, prefix="/phone", tags=["phone"])
api_router.include_router(sms.router, prefix="/sms", tags=["sms"])
api_router.include_router(email.router, prefix="/email", tags=["email"])

api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)
