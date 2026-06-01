"""
Router /fraud — Endpoints pour la synchronisation offline des numéros frauduleux.
Chemin complet : /api/v1/fraud/numbers/list
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.api.deps.auth_deps import get_current_user
from app.models.fraud import FraudulentNumber
from app.models.user import User
from app.services.cache import cache_service

router = APIRouter()


class FraudNumberItem(BaseModel):
    phone_number: str
    label: Optional[str] = None
    fraud_type: Optional[str] = None


class FraudNumberListResponse(BaseModel):
    numbers: List[FraudNumberItem]
    generated_at: str
    version: int
    total: int


@router.get("/numbers/list", response_model=FraudNumberListResponse)
async def get_fraud_number_list(
    limit: int = Query(5000, ge=1, le=20000, description="Nombre maximum de numéros"),
    country_code: Optional[str] = Query(None, description="Filtrer par pays (ex: MG, FR)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Liste des numéros frauduleux vérifiés pour la synchronisation offline des apps mobiles.

    - Retourne uniquement les numéros **vérifiés** (verified=true)
    - Triés par nombre de signalements décroissant
    - Cache Redis 6h pour minimiser la charge DB

    **Accès:** USER authentifié
    """
    cache_key = f"fraud_list:{country_code or 'all'}:{limit}"
    cached = await cache_service.get(cache_key)
    if cached:
        return FraudNumberListResponse(**cached)

    query = select(FraudulentNumber).where(FraudulentNumber.verified == True)
    if country_code:
        query = query.where(FraudulentNumber.country_code == country_code.upper())

    query = query.order_by(FraudulentNumber.report_count.desc()).limit(limit)

    result = await db.execute(query)
    numbers = result.scalars().all()

    items = [
        FraudNumberItem(
            phone_number=n.phone_number,
            label=f"Signalé {n.report_count} fois — {n.fraud_type.value}",
            fraud_type=n.fraud_type.value,
        )
        for n in numbers
    ]

    response_data = {
        "numbers": [i.model_dump() for i in items],
        "generated_at": datetime.utcnow().isoformat(),
        "version": 1,
        "total": len(items),
    }

    # Cache 6h — la liste évolue lentement
    await cache_service.set(cache_key, response_data, expire=21600)

    return FraudNumberListResponse(**response_data)
