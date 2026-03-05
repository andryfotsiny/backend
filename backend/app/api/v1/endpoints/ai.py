from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.ai_service import ai_service
from app.api.deps.auth_deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Interagir avec l'IA de DYLETH.
    Permet de poser des questions sur les détections, les statistiques ou le fonctionnement du système.
    """
    result = await ai_service.get_response(db, request.message, request.user_id)
    return ChatResponse(**result)
