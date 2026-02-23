from fastapi import APIRouter
from app.api.v1.endpoints.phone import router as phone_router
from app.api.v1.endpoints.sms import router as sms_router
from app.api.v1.endpoints.email import router as email_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.recent import router as recent_router
from app.api.v1.endpoints import analytics

api_router = APIRouter()

print("DEBUG: Registering routers in /api/v1")
api_router.include_router(phone_router, prefix="/phone", tags=["phone"])
api_router.include_router(sms_router, prefix="/sms", tags=["sms"])
api_router.include_router(email_router, prefix="/email", tags=["email"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(recent_router, prefix="/recent", tags=["recent"])


api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)
