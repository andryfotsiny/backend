# backend/app/api/v1/endpoints/recent.py
"""
Endpoints pour récupérer les détections récentes - VERSION SIMPLIFIÉE
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.api.deps.auth_deps import get_db, get_current_user
from app.models.user import User
from app.models.fraud import FraudulentNumber, FraudulentDomain
from app.models.report import DetectionLog

router = APIRouter()


# === SCHEMAS ===


class RecentCall(BaseModel):
    """Appel récent détecté"""

    number: str
    country: str
    type: str
    status: str  # 'blocked', 'suspicious', 'verified'
    reports: int
    timestamp: str


class RecentSms(BaseModel):
    """SMS récent détecté"""

    preview: str
    type: str
    sender: str
    hasLink: bool
    riskLevel: str  # 'critical', 'high', 'medium', 'low'
    timestamp: str


class RecentEmail(BaseModel):
    """Email récent détecté"""

    subject: str
    sender: str
    realDomain: Optional[str]
    hasAttachment: bool
    riskLevel: str
    timestamp: str


@router.get("/phone/recent-logs", response_model=List[RecentCall])
async def get_recent_calls_logs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les appels récents détectés

    - **limit**: Nombre de résultats (max 50)
    - **offset**: Pagination
    """

    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "phone")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_calls = []
    for detection in detections:
        phone = (
            detection.meta_data.get("phone", "Unknown")
            if detection.meta_data
            else "Unknown"
        )

        if detection.is_fraud and detection.confidence > 0.8:
            status = "blocked"
        elif detection.is_fraud and detection.confidence > 0.5:
            status = "suspicious"
        else:
            status = "verified"

        fraud_query = select(FraudulentNumber).where(
            FraudulentNumber.phone_number == phone
        )
        fraud_result = await db.execute(fraud_query)
        fraud_data = fraud_result.scalar_one_or_none()

        recent_calls.append(
            RecentCall(
                number=phone,
                country=fraud_data.country_code if fraud_data else "FR",
                type=fraud_data.fraud_type.value if fraud_data else "unknown",
                status=status,
                reports=fraud_data.report_count if fraud_data else 0,
                timestamp=detection.timestamp.isoformat(),
            )
        )

    return recent_calls


@router.get("/sms/recent-logs", response_model=List[RecentSms])
async def get_recent_sms_logs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les SMS récents détectés
    """

    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "sms")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_sms = []
    for detection in detections:
        meta = detection.meta_data or {}
        content = meta.get("content", "")

        # Déterminer le risk_level
        if detection.is_fraud and detection.confidence > 0.9:
            risk_level = "critical"
        elif detection.is_fraud and detection.confidence > 0.7:
            risk_level = "high"
        elif detection.is_fraud and detection.confidence > 0.5:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Vérifier si contient un lien
        has_link = any(
            word in content.lower() for word in ["http", "bit.ly", "www.", ".com"]
        )

        recent_sms.append(
            RecentSms(
                preview=content[:100] if content else "Contenu non disponible",
                type=meta.get("category", "unknown"),
                sender=meta.get("sender", "Unknown"),
                hasLink=has_link,
                riskLevel=risk_level,
                timestamp=detection.timestamp.isoformat(),
            )
        )

    return recent_sms


@router.get("/email/recent-logs", response_model=List[RecentEmail])
async def get_recent_emails_logs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les emails récents détectés
    """

    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "email")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_emails = []
    for detection in detections:
        meta = detection.meta_data or {}
        sender = meta.get("sender", "unknown@example.com")
        domain = sender.split("@")[1] if "@" in sender else sender
        domain_query = select(FraudulentDomain).where(FraudulentDomain.domain == domain)
        domain_result = await db.execute(domain_query)
        fraud_domain = domain_result.scalar_one_or_none()

        if detection.is_fraud and detection.confidence > 0.9:
            risk_level = "critical"
        elif detection.is_fraud and detection.confidence > 0.7:
            risk_level = "high"
        elif detection.is_fraud and detection.confidence > 0.5:
            risk_level = "medium"
        else:
            risk_level = "low"

        recent_emails.append(
            RecentEmail(
                subject=meta.get("subject", "No subject"),
                sender=sender,
                realDomain=domain if fraud_domain else None,
                hasAttachment=meta.get("has_attachment", False),
                riskLevel=risk_level,
                timestamp=detection.timestamp.isoformat(),
            )
        )

    return recent_emails


@router.get("/phone/recent-simple", response_model=List[RecentCall])
async def get_recent_calls_simple(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Version simplifiée : récupère les derniers numéros frauduleux ajoutés
    """

    query = (
        select(FraudulentNumber)
        .order_by(desc(FraudulentNumber.last_reported))
        .limit(limit)
    )

    result = await db.execute(query)
    numbers = result.scalars().all()

    recent_calls = []
    for number in numbers:
        phone_masked = number.phone_number[:6] + " ** ** " + number.phone_number[-2:]

        status = "blocked" if number.confidence_score > 0.8 else "suspicious"

        recent_calls.append(
            RecentCall(
                number=phone_masked,
                country=number.country_code,
                type=number.fraud_type.value,
                status=status,
                reports=number.report_count or 0,
                timestamp=number.last_reported.isoformat()
                if number.last_reported
                else "",
            )
        )

    return recent_calls


@router.get("/email/recent-simple", response_model=List[RecentEmail])
async def get_recent_emails_simple(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Version simplifiée : récupère les derniers domaines frauduleux
    """

    query = (
        select(FraudulentDomain)
        .order_by(desc(FraudulentDomain.first_seen))
        .limit(limit)
    )

    result = await db.execute(query)
    domains = result.scalars().all()

    recent_emails = []
    for domain in domains:
        sender = f"noreply@{domain.domain}"

        risk_level = (
            "critical"
            if domain.reputation_score and domain.reputation_score < 0.3
            else "high"
        )

        recent_emails.append(
            RecentEmail(
                subject=f"Suspicious email from {domain.domain}",
                sender=sender,
                realDomain=domain.domain,
                hasAttachment=False,
                riskLevel=risk_level,
                timestamp=domain.first_seen.isoformat() if domain.first_seen else "",
            )
        )

    return recent_emails
