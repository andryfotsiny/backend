from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps.role_deps import require_organisation
from app.models.user import User
from app.models.fraud import FraudulentNumber, FraudulentDomain, FraudType
from app.services.cache import cache_service

router = APIRouter()


# === SCHEMAS ===

class BlacklistPhoneCreate(BaseModel):
    phone_number: str
    country_code: str
    fraud_type: FraudType
    confidence_score: float = 0.99
    source: Optional[str] = "manual"

class BlacklistPhoneResponse(BaseModel):
    phone_number: str
    country_code: str
    fraud_type: str
    confidence_score: float
    verified: bool
    source: Optional[str]
    created: bool  # True = nouveau, False = déjà existant (mis à jour)

class BlacklistDomainCreate(BaseModel):
    domain: str
    phishing_type: Optional[str] = None
    reputation_score: float = 0.99

class BlacklistDomainResponse(BaseModel):
    domain: str
    phishing_type: Optional[str]
    reputation_score: float
    created: bool


# === PHONE ===

@router.post("/phone", response_model=BlacklistPhoneResponse)
async def blacklist_phone(
    payload: BlacklistPhoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Ajouter ou mettre à jour un numéro directement dans la blacklist.
    **Accès:** ADMIN / ORGANISATION
    """
    result = await db.execute(
        select(FraudulentNumber).where(
            FraudulentNumber.phone_number == payload.phone_number
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.fraud_type = payload.fraud_type
        existing.confidence_score = payload.confidence_score
        existing.verified = True
        existing.last_reported = datetime.utcnow()
        existing.source = payload.source
        await db.commit()
        await db.refresh(existing)
        await cache_service.delete(f"phone:{payload.phone_number}")
        return BlacklistPhoneResponse(
            phone_number=existing.phone_number,
            country_code=existing.country_code,
            fraud_type=existing.fraud_type.value,
            confidence_score=existing.confidence_score,
            verified=existing.verified,
            source=existing.source,
            created=False,
        )

    new_entry = FraudulentNumber(
        phone_number=payload.phone_number,
        country_code=payload.country_code,
        fraud_type=payload.fraud_type,
        confidence_score=payload.confidence_score,
        report_count=1,
        verified=True,
        first_reported=datetime.utcnow(),
        last_reported=datetime.utcnow(),
        source=payload.source,
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)
    await cache_service.delete(f"phone:{payload.phone_number}")

    return BlacklistPhoneResponse(
        phone_number=new_entry.phone_number,
        country_code=new_entry.country_code,
        fraud_type=new_entry.fraud_type.value,
        confidence_score=new_entry.confidence_score,
        verified=new_entry.verified,
        source=new_entry.source,
        created=True,
    )


@router.delete("/phone/{phone_number}")
async def remove_phone_from_blacklist(
    phone_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Retirer un numéro de la blacklist.
    **Accès:** ADMIN / ORGANISATION
    """
    result = await db.execute(
        select(FraudulentNumber).where(
            FraudulentNumber.phone_number == phone_number
        )
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Numéro non trouvé dans la blacklist")

    await db.execute(
        delete(FraudulentNumber).where(
            FraudulentNumber.phone_number == phone_number
        )
    )
    await db.commit()
    await cache_service.delete(f"phone:{phone_number}")

    return {"message": f"{phone_number} retiré de la blacklist"}


# === EMAIL / DOMAIN ===

@router.post("/domain", response_model=BlacklistDomainResponse)
async def blacklist_domain(
    payload: BlacklistDomainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Ajouter ou mettre à jour un domaine directement dans la blacklist.
    **Accès:** ADMIN / ORGANISATION
    """
    result = await db.execute(
        select(FraudulentDomain).where(
            FraudulentDomain.domain == payload.domain
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.phishing_type = payload.phishing_type
        existing.reputation_score = payload.reputation_score
        existing.blocked_count = (existing.blocked_count or 0) + 1
        await db.commit()
        await db.refresh(existing)
        return BlacklistDomainResponse(
            domain=existing.domain,
            phishing_type=existing.phishing_type,
            reputation_score=existing.reputation_score,
            created=False,
        )

    new_entry = FraudulentDomain(
        domain=payload.domain,
        phishing_type=payload.phishing_type,
        reputation_score=payload.reputation_score,
        first_seen=datetime.utcnow(),
        blocked_count=1,
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    return BlacklistDomainResponse(
        domain=new_entry.domain,
        phishing_type=new_entry.phishing_type,
        reputation_score=new_entry.reputation_score,
        created=True,
    )


@router.delete("/domain/{domain}")
async def remove_domain_from_blacklist(
    domain: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Retirer un domaine de la blacklist.
    **Accès:** ADMIN / ORGANISATION
    """
    result = await db.execute(
        select(FraudulentDomain).where(FraudulentDomain.domain == domain)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Domaine non trouvé dans la blacklist")

    await db.execute(
        delete(FraudulentDomain).where(FraudulentDomain.domain == domain)
    )
    await db.commit()

    return {"message": f"{domain} retiré de la blacklist"}