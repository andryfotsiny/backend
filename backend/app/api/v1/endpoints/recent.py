# backend/app/api/v1/endpoints/recent.py
"""
Endpoints pour récupérer les détections récentes - VERSION SIMPLIFIÉE
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

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


# === ENDPOINTS ===

@router.get("/phone/recent", response_model=List[RecentCall])
async def get_recent_calls(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les derniers numéros frauduleux ajoutés
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
        # Masquer partiellement le numéro
        phone_display = number.phone_number
        if len(phone_display) > 8:
            phone_display = phone_display[:6] + " ** ** " + phone_display[-2:]

        # Déterminer le status basé sur confidence
        if number.confidence_score > 0.8:
            status = "blocked"
        elif number.confidence_score > 0.5:
            status = "suspicious"
        else:
            status = "verified"

        # Calculer temps écoulé
        if number.last_reported:
            elapsed = datetime.now() - number.last_reported
            if elapsed.total_seconds() < 3600:
                timestamp = f"Il y a {int(elapsed.total_seconds() / 60)} min"
            elif elapsed.total_seconds() < 86400:
                timestamp = f"Il y a {int(elapsed.total_seconds() / 3600)} h"
            else:
                timestamp = f"Il y a {elapsed.days} jours"
        else:
            timestamp = "Date inconnue"

        recent_calls.append(RecentCall(
            number=phone_display,
            country=number.country_code,
            type=number.fraud_type.value if hasattr(number.fraud_type, 'value') else str(number.fraud_type),
            status=status,
            reports=number.report_count or 0,
            timestamp=timestamp
        ))

    return recent_calls


@router.get("/sms/recent", response_model=List[RecentSms])
async def get_recent_sms(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les derniers SMS frauduleux détectés
    """

    # Récupérer depuis detection_logs avec type SMS
    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "sms")
        .where(DetectionLog.is_fraud == True)
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
    )

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_sms = []
    for detection in detections:
        # Extraire données depuis user_reports si disponible
        # Sinon générer des données de démo

        # Déterminer risk level
        if detection.confidence > 0.9:
            risk_level = "critical"
        elif detection.confidence > 0.7:
            risk_level = "high"
        elif detection.confidence > 0.5:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Calculer temps écoulé
        if detection.timestamp:
            elapsed = datetime.now() - detection.timestamp
            if elapsed.total_seconds() < 3600:
                timestamp_str = f"Il y a {int(elapsed.total_seconds() / 60)} min"
            elif elapsed.total_seconds() < 86400:
                timestamp_str = f"Il y a {int(elapsed.total_seconds() / 3600)} h"
            else:
                timestamp_str = f"Il y a {elapsed.days} jours"
        else:
            timestamp_str = "Date inconnue"

        recent_sms.append(RecentSms(
            preview="SMS frauduleux détecté par le système",  # À adapter avec vos données
            type="Phishing" if risk_level == "critical" else "Spam",
            sender="+33 6 ** ** ** **",
            hasLink=True,  # À adapter
            riskLevel=risk_level,
            timestamp=timestamp_str
        ))

    return recent_sms


@router.get("/email/recent", response_model=List[RecentEmail])
async def get_recent_emails(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les derniers emails frauduleux
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
        # Déterminer risk level
        if domain.reputation_score and domain.reputation_score < 0.3:
            risk_level = "critical"
        elif domain.reputation_score and domain.reputation_score < 0.6:
            risk_level = "high"
        else:
            risk_level = "medium"

        # Calculer temps écoulé
        if domain.first_seen:
            elapsed = datetime.now() - domain.first_seen
            if elapsed.total_seconds() < 3600:
                timestamp_str = f"Il y a {int(elapsed.total_seconds() / 60)} min"
            elif elapsed.total_seconds() < 86400:
                timestamp_str = f"Il y a {int(elapsed.total_seconds() / 3600)} h"
            else:
                timestamp_str = f"Il y a {elapsed.days} jours"
        else:
            timestamp_str = "Date inconnue"

        recent_emails.append(RecentEmail(
            subject=f"Email suspect de {domain.domain}",
            sender=f"noreply@{domain.domain}",
            realDomain=domain.domain,
            hasAttachment=False,
            riskLevel=risk_level,
            timestamp=timestamp_str
        ))

    return recent_emails


# === ENDPOINTS ===

@router.get("/phone/recent", response_model=List[RecentCall])
async def get_recent_calls(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupérer les appels récents détectés

    - **limit**: Nombre de résultats (max 50)
    - **offset**: Pagination
    """

    # Récupérer les détections récentes de type 'phone'
    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "phone")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    detections = result.scalars().all()

    # Transformer en RecentCall
    recent_calls = []
    for detection in detections:
        # Extraire le numéro depuis les métadonnées (à adapter selon votre structure)
        phone = detection.meta_data.get("phone", "Unknown") if detection.meta_data else "Unknown"

        # Déterminer le status
        if detection.is_fraud and detection.confidence > 0.8:
            status = "blocked"
        elif detection.is_fraud and detection.confidence > 0.5:
            status = "suspicious"
        else:
            status = "verified"

        # Récupérer les infos depuis fraudulent_numbers si disponible
        fraud_query = select(FraudulentNumber).where(FraudulentNumber.phone_number == phone)
        fraud_result = await db.execute(fraud_query)
        fraud_data = fraud_result.scalar_one_or_none()

        recent_calls.append(RecentCall(
            phone=phone,
            country=fraud_data.country_code if fraud_data else "FR",
            type=fraud_data.fraud_type.value if fraud_data else "unknown",
            status=status,
            reports=fraud_data.report_count if fraud_data else 0,
            timestamp=detection.timestamp.isoformat(),
            is_fraud=detection.is_fraud,
            confidence=detection.confidence
        ))

    return recent_calls


@router.get("/sms/recent", response_model=List[RecentSms])
async def get_recent_sms(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        has_link = any(word in content.lower() for word in ["http", "bit.ly", "www.", ".com"])

        recent_sms.append(RecentSms(
            preview=content[:100] if content else "Contenu non disponible",
            type=meta.get("category", "unknown"),
            sender=meta.get("sender", "Unknown"),
            has_link=has_link,
            risk_level=risk_level,
            timestamp=detection.timestamp.isoformat(),
            is_fraud=detection.is_fraud,
            confidence=detection.confidence
        ))

    return recent_sms


@router.get("/email/recent", response_model=List[RecentEmail])
async def get_recent_emails(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

        # Extraire le domaine
        domain = sender.split("@")[1] if "@" in sender else sender

        # Vérifier si le domaine est frauduleux
        domain_query = select(FraudulentDomain).where(FraudulentDomain.domain == domain)
        domain_result = await db.execute(domain_query)
        fraud_domain = domain_result.scalar_one_or_none()

        # Déterminer le risk_level
        if detection.is_fraud and detection.confidence > 0.9:
            risk_level = "critical"
        elif detection.is_fraud and detection.confidence > 0.7:
            risk_level = "high"
        elif detection.is_fraud and detection.confidence > 0.5:
            risk_level = "medium"
        else:
            risk_level = "low"

        recent_emails.append(RecentEmail(
            subject=meta.get("subject", "No subject"),
            sender=sender,
            real_domain=domain if fraud_domain else None,
            has_attachment=meta.get("has_attachment", False),
            risk_level=risk_level,
            timestamp=detection.timestamp.isoformat(),
            is_fraud=detection.is_fraud,
            confidence=detection.confidence,
            phishing_type=fraud_domain.phishing_type if fraud_domain else None
        ))

    return recent_emails


# === ALTERNATIVE : Si vous n'avez pas de DetectionLog ===

@router.get("/phone/recent-simple", response_model=List[RecentCall])
async def get_recent_calls_simple(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        # Masquer partiellement le numéro
        phone_masked = number.phone_number[:6] + " ** ** " + number.phone_number[-2:]

        status = "blocked" if number.confidence_score > 0.8 else "suspicious"

        recent_calls.append(RecentCall(
            phone=phone_masked,
            country=number.country_code,
            type=number.fraud_type.value,
            status=status,
            reports=number.report_count or 0,
            timestamp=number.last_reported.isoformat() if number.last_reported else "",
            is_fraud=True,
            confidence=number.confidence_score
        ))

    return recent_calls


@router.get("/email/recent-simple", response_model=List[RecentEmail])
async def get_recent_emails_simple(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        # Créer un faux sender
        sender = f"noreply@{domain.domain}"

        risk_level = "critical" if domain.reputation_score and domain.reputation_score < 0.3 else "high"

        recent_emails.append(RecentEmail(
            subject=f"Suspicious email from {domain.domain}",
            sender=sender,
            real_domain=domain.domain,
            has_attachment=False,
            risk_level=risk_level,
            timestamp=domain.first_seen.isoformat() if domain.first_seen else "",
            is_fraud=True,
            confidence=0.9,
            phishing_type=domain.phishing_type
        ))

    return recent_emails