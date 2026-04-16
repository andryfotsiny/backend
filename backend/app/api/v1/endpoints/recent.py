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


@router.get("/phone/recent-logs", response_model=List[RecentCall])
async def get_recent_calls_logs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "phone")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )
    if user_id:
        query = query.where(DetectionLog.user_id == user_id)

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_calls = []
    for detection in detections:
        report_query = (
            select(UserReport)
            .where(UserReport.user_id == detection.user_id)
            .where(UserReport.report_type == "call")
            .order_by(desc(UserReport.timestamp))
            .limit(1)
        )
        report_result = await db.execute(report_query)
        user_report = report_result.scalar_one_or_none()

        phone = "Unknown"
        if user_report:
            if user_report.phone_number:
                phone = user_report.phone_number
            elif user_report.meta_data:
                phone = user_report.meta_data.get("phone", "Unknown")

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
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "sms")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )
    if user_id:
        query = query.where(DetectionLog.user_id == user_id)

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_sms = []
    for detection in detections:
        report_query = (
            select(UserReport)
            .where(UserReport.user_id == detection.user_id)
            .where(UserReport.report_type == "sms")
            .order_by(desc(UserReport.timestamp))
            .limit(1)
        )
        report_result = await db.execute(report_query)
        user_report = report_result.scalar_one_or_none()

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
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "email")
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
        .offset(offset)
    )
    if user_id:
        query = query.where(DetectionLog.user_id == user_id)

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_emails = []
    for detection in detections:
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


@router.get("/sms/recent-simple", response_model=List[RecentSms])
async def get_recent_sms_simple(
    limit: int = Query(10, ge=1, le=50),
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(DetectionLog)
        .where(DetectionLog.detection_type == "sms")
        .where(DetectionLog.is_fraud)
        .order_by(desc(DetectionLog.timestamp))
        .limit(limit)
    )
    if user_id:
        query = query.where(DetectionLog.user_id == user_id)

    result = await db.execute(query)
    detections = result.scalars().all()

    recent_sms = []
    for detection in detections:
        meta = detection.meta_data or {}
        content = meta.get("content", "Pas de contenu")
        has_link = any(
            word in content.lower() for word in ["http", "bit.ly", "www.", ".com"]
        )
        recent_sms.append(
            RecentSms(
                preview=content[:100],
                type=meta.get("category", "phishing"),
                sender=meta.get("sender", "Inconnu"),
                hasLink=has_link,
                riskLevel=_confidence_to_risk(detection.is_fraud, detection.confidence),
                timestamp=detection.timestamp.isoformat() if detection.timestamp else "",
            )
        )

    return recent_sms


@router.get("/phone/recent-simple", response_model=List[RecentCall])
async def get_recent_calls_simple(
    limit: int = Query(10, ge=1, le=50),
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id:
        query = (
            select(UserReport, FraudulentNumber)
            .outerjoin(
                FraudulentNumber,
                UserReport.phone_number == FraudulentNumber.phone_number
            )
            .where(UserReport.user_id == user_id)
            .where(UserReport.report_type == "call")
            .order_by(desc(UserReport.timestamp))
            .limit(limit)
        )
        result = await db.execute(query)
        rows = result.all()

        recent_calls = []
        for user_report, fraud_data in rows:
            phone = user_report.phone_number or "Unknown"
            status = "blocked" if fraud_data and fraud_data.confidence_score > 0.8 else "suspicious"
            recent_calls.append(
                RecentCall(
                    number=phone,
                    country=fraud_data.country_code if fraud_data else "??",
                    type=fraud_data.fraud_type.value if fraud_data else "unknown",
                    status=status,
                    reports=fraud_data.report_count if fraud_data else 0,
                    timestamp=user_report.timestamp.isoformat() if user_report.timestamp else "",
                )
            )
        return recent_calls

    query = (
        select(FraudulentNumber)
        .order_by(desc(FraudulentNumber.last_reported))
        .limit(limit)
    )
    result = await db.execute(query)
    numbers = result.scalars().all()

    recent_calls = []
    for number in numbers:
        status = "blocked" if number.confidence_score > 0.8 else "suspicious"
        recent_calls.append(
            RecentCall(
                number=number.phone_number,
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
    user_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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