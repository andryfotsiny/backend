from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, asc, desc
from typing import Optional, List
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
    created: bool

class BlacklistPhoneItem(BaseModel):
    phone_number: str
    country_code: str
    fraud_type: str
    confidence_score: float
    report_count: Optional[int]
    verified: Optional[bool]
    source: Optional[str]
    first_reported: Optional[str]
    last_reported: Optional[str]

class BlacklistPhoneList(BaseModel):
    items: List[BlacklistPhoneItem]
    total: int
    skip: int
    limit: int

class BlacklistDomainCreate(BaseModel):
    domain: str
    phishing_type: Optional[str] = None
    reputation_score: float = 0.99

class BlacklistDomainResponse(BaseModel):
    domain: str
    phishing_type: Optional[str]
    reputation_score: float
    created: bool

class BlacklistDomainItem(BaseModel):
    domain: str
    phishing_type: Optional[str]
    reputation_score: Optional[float]
    blocked_count: Optional[int]
    first_seen: Optional[str]

class BlacklistDomainList(BaseModel):
    items: List[BlacklistDomainItem]
    total: int
    skip: int
    limit: int


# === PHONE ===

@router.get("/phone", response_model=BlacklistPhoneList)
async def list_blacklisted_phones(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None, description="Recherche sur le numéro (iLike)"),
    country_code: Optional[str] = Query(None),
    fraud_type: Optional[str] = Query(None),
    verified: Optional[bool] = Query(None),
    date_from: Optional[datetime] = Query(None, description="Filtre first_reported >= date_from"),
    date_to: Optional[datetime] = Query(None, description="Filtre first_reported <= date_to"),
    order_by: str = Query("last_reported", regex="^(phone_number|country_code|fraud_type|confidence_score|report_count|first_reported|last_reported)$"),
    order_dir: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Liste les numéros blacklistés.
    - **search** : recherche partielle sur le numéro
    - **country_code** : filtre par pays
    - **fraud_type** : filtre par type de fraude
    - **verified** : filtre true/false
    - **date_from / date_to** : filtre sur first_reported
    - **order_by / order_dir** : tri
    **Accès:** ADMIN / ORGANISATION
    """
    query = select(FraudulentNumber)
    count_query = select(func.count(FraudulentNumber.phone_number))

    if search:
        query = query.where(FraudulentNumber.phone_number.ilike(f"%{search}%"))
        count_query = count_query.where(FraudulentNumber.phone_number.ilike(f"%{search}%"))
    if country_code:
        query = query.where(FraudulentNumber.country_code == country_code)
        count_query = count_query.where(FraudulentNumber.country_code == country_code)
    if fraud_type:
        query = query.where(FraudulentNumber.fraud_type == fraud_type)
        count_query = count_query.where(FraudulentNumber.fraud_type == fraud_type)
    if verified is not None:
        query = query.where(FraudulentNumber.verified == verified)
        count_query = count_query.where(FraudulentNumber.verified == verified)
    if date_from:
        query = query.where(FraudulentNumber.first_reported >= date_from)
        count_query = count_query.where(FraudulentNumber.first_reported >= date_from)
    if date_to:
        query = query.where(FraudulentNumber.first_reported <= date_to)
        count_query = count_query.where(FraudulentNumber.first_reported <= date_to)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    sort_col = getattr(FraudulentNumber, order_by)
    query = query.order_by(desc(sort_col) if order_dir == "desc" else asc(sort_col))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    numbers = result.scalars().all()

    return BlacklistPhoneList(
        items=[
            BlacklistPhoneItem(
                phone_number=n.phone_number,
                country_code=n.country_code,
                fraud_type=n.fraud_type.value,
                confidence_score=n.confidence_score,
                report_count=n.report_count,
                verified=n.verified,
                source=n.source,
                first_reported=n.first_reported.isoformat() if n.first_reported else None,
                last_reported=n.last_reported.isoformat() if n.last_reported else None,
            )
            for n in numbers
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/phone/{phone_number}", response_model=BlacklistPhoneItem)
async def get_blacklisted_phone(
    phone_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Détail d'un numéro blacklisté.
    **Accès:** ADMIN / ORGANISATION
    """
    result = await db.execute(
        select(FraudulentNumber).where(
            FraudulentNumber.phone_number == phone_number
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Numéro non trouvé dans la blacklist")

    return BlacklistPhoneItem(
        phone_number=entry.phone_number,
        country_code=entry.country_code,
        fraud_type=entry.fraud_type.value,
        confidence_score=entry.confidence_score,
        report_count=entry.report_count,
        verified=entry.verified,
        source=entry.source,
        first_reported=entry.first_reported.isoformat() if entry.first_reported else None,
        last_reported=entry.last_reported.isoformat() if entry.last_reported else None,
    )


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

@router.get("/domain", response_model=BlacklistDomainList)
async def list_blacklisted_domains(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None, description="Recherche sur le domaine (iLike)"),
    phishing_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None, description="Filtre first_seen >= date_from"),
    date_to: Optional[datetime] = Query(None, description="Filtre first_seen <= date_to"),
    order_by: str = Query("first_seen", regex="^(domain|phishing_type|reputation_score|blocked_count|first_seen)$"),
    order_dir: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Liste les domaines blacklistés.
    - **search** : recherche partielle sur le domaine
    - **phishing_type** : filtre par type de phishing
    - **date_from / date_to** : filtre sur first_seen
    - **order_by / order_dir** : tri
    **Accès:** ADMIN / ORGANISATION
    """
    query = select(FraudulentDomain)
    count_query = select(func.count(FraudulentDomain.domain))

    if search:
        query = query.where(FraudulentDomain.domain.ilike(f"%{search}%"))
        count_query = count_query.where(FraudulentDomain.domain.ilike(f"%{search}%"))
    if phishing_type:
        query = query.where(FraudulentDomain.phishing_type == phishing_type)
        count_query = count_query.where(FraudulentDomain.phishing_type == phishing_type)
    if date_from:
        query = query.where(FraudulentDomain.first_seen >= date_from)
        count_query = count_query.where(FraudulentDomain.first_seen >= date_from)
    if date_to:
        query = query.where(FraudulentDomain.first_seen <= date_to)
        count_query = count_query.where(FraudulentDomain.first_seen <= date_to)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    sort_col = getattr(FraudulentDomain, order_by)
    query = query.order_by(desc(sort_col) if order_dir == "desc" else asc(sort_col))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    domains = result.scalars().all()

    return BlacklistDomainList(
        items=[
            BlacklistDomainItem(
                domain=d.domain,
                phishing_type=d.phishing_type,
                reputation_score=d.reputation_score,
                blocked_count=d.blocked_count,
                first_seen=d.first_seen.isoformat() if d.first_seen else None,
            )
            for d in domains
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/domain/{domain}", response_model=BlacklistDomainItem)
async def get_blacklisted_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_organisation),
):
    """
    Détail d'un domaine blacklisté.
    **Accès:** ADMIN / ORGANISATION
    """
    result = await db.execute(
        select(FraudulentDomain).where(FraudulentDomain.domain == domain)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Domaine non trouvé dans la blacklist")

    return BlacklistDomainItem(
        domain=entry.domain,
        phishing_type=entry.phishing_type,
        reputation_score=entry.reputation_score,
        blocked_count=entry.blocked_count,
        first_seen=entry.first_seen.isoformat() if entry.first_seen else None,
    )


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