# backend/app/api/v1/endpoints/recent.py
"""
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.api.deps.auth_deps import get_db, get_current_user
from app.models.user import User
from app.models.fraud import FraudulentNumber, FraudulentDomain
from app.models.report import DetectionLog, UserReport

router = APIRouter()


# === SCHEMAS ===


class RecentCall(BaseModel):
    number: str
    country: str
    type: str
    status: str
    reports: int
    timestamp: str


class RecentSms(BaseModel):
    preview: str
    type: str
    sender: str
    hasLink: bool
    riskLevel: str
    timestamp: str


class RecentEmail(BaseModel):
    subject: str
    sender: str
    realDomain: Optional[str]
    hasAttachment: bool
    riskLevel: str
    timestamp: str


# === HELPERS ===

def _confidence_to_status(is_fraud: bool, confidence: float) -> str:
    if is_fraud and confidence > 0.8:
        return "blocked"
    elif is_fraud and confidence > 0.5:
        return "suspicious"
    return "verified"


def _confidence_to_risk(is_fraud: bool, confidence: float) -> str:
    if is_fraud and confidence > 0.9:
        return "critical"
    elif is_fraud and confidence > 0.7:
        return "high"
    elif is_fraud and confidence > 0.5:
        return "medium"
    return "low"


# === ENDPOINTS ===


@router.get("/phone/recent-logs", response_model=List[RecentCall])
async def get_recent_calls_logs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Récupérer les appels récents détectés
    Fix: jointure avec UserReport pour récupérer le numéro de téléphone
    """
    # Récupérer les DetectionLog de type phone
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
        # Récupérer le UserReport associé pour avoir le numéro (meta_data est sur UserReport)
        report_query = (
            select(UserReport)
            .where(UserReport.user_id == detection.user_id)
            .where(UserReport.report_type == "call")
            .order_by(desc(UserReport.timestamp))
            .limit(1)
        )
        report_result = await db.execute(report_query)
        user_report = report_result.scalar_one_or_none()

        # Extraire le numéro depuis UserReport.meta_data ou UserReport.phone_number
        phone = "Unknown"
        if user_report:
            if user_report.phone_number:
                phone = user_report.phone_number
            elif user_report.meta_data:
                phone = user_report.meta_data.get("phone", "Unknown")

        # Chercher dans fraudulent_numbers pour enrichir
        fraud_query = select(FraudulentNumber).where(
            FraudulentNumber.phone_number == phone
        )
        fraud_result = await db.execute(fraud_query)
        fraud_data = fraud_result.scalar_one_or_none()

        recent_calls.append(
            RecentCall(
                number=phone,
                country=fraud_data.country_code if fraud_data else "??",
                type=fraud_data.fraud_type.value if fraud_data else "unknown",
                status=_confidence_to_status(detection.is_fraud, detection.confidence),
                reports=fraud_data.report_count if fraud_data else 0,
                timestamp=detection.timestamp.isoformat() if detection.timestamp else "",
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
    Fix: meta_data est sur UserReport, pas sur DetectionLog
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
        # Récupérer le UserReport associé pour avoir le contenu SMS
        report_query = (
            select(UserReport)
            .where(UserReport.user_id == detection.user_id)
            .where(UserReport.report_type == "sms")
            .order_by(desc(UserReport.timestamp))
            .limit(1)
        )
        report_result = await db.execute(report_query)
        user_report = report_result.scalar_one_or_none()

        # Extraire les données depuis UserReport.meta_data
        meta = {}
        if user_report and user_report.meta_data:
            meta = user_report.meta_data

        content = meta.get("content", "")
        has_link = any(
            word in content.lower() for word in ["http", "bit.ly", "www.", ".com"]
        )

        recent_sms.append(
            RecentSms(
                preview=content[:100] if content else "Contenu non disponible",
                type=meta.get("category", "unknown"),
                sender=meta.get("sender", "Unknown"),
                hasLink=has_link,
                riskLevel=_confidence_to_risk(detection.is_fraud, detection.confidence),
                timestamp=detection.timestamp.isoformat() if detection.timestamp else "",
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
    Fix: meta_data est sur UserReport, pas sur DetectionLog
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
        # Récupérer le UserReport associé
        report_query = (
            select(UserReport)
            .where(UserReport.user_id == detection.user_id)
            .order_by(desc(UserReport.timestamp))
            .limit(1)
        )
        report_result = await db.execute(report_query)
        user_report = report_result.scalar_one_or_none()

        meta = {}
        if user_report and user_report.meta_data:
            meta = user_report.meta_data

        sender = meta.get("sender", "unknown@example.com")
        domain = sender.split("@")[1] if "@" in sender else sender

        # Vérifier si le domaine est dans fraudulent_domains
        domain_query = select(FraudulentDomain).where(FraudulentDomain.domain == domain)
        domain_result = await db.execute(domain_query)
        fraud_domain = domain_result.scalar_one_or_none()

        recent_emails.append(
            RecentEmail(
                subject=meta.get("subject", "No subject"),
                sender=sender,
                realDomain=domain if fraud_domain else None,
                hasAttachment=meta.get("has_attachment", False),
                riskLevel=_confidence_to_risk(detection.is_fraud, detection.confidence),
                timestamp=detection.timestamp.isoformat() if detection.timestamp else "",
            )
        )

    return recent_emails


@router.get("/phone/recent-simple", response_model=List[RecentCall])
async def get_recent_calls_simple(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Version simplifiée : derniers numéros frauduleux ajoutés"""
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
                timestamp=number.last_reported.isoformat() if number.last_reported else "",
            )
        )

    return recent_calls


@router.get("/email/recent-simple", response_model=List[RecentEmail])
async def get_recent_emails_simple(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Version simplifiée : derniers domaines frauduleux"""
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