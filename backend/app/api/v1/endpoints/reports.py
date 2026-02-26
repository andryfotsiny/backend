import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.session import get_db
from app.models.report import UserReport, VerificationStatus, ReportType
from app.models.fraud import FraudulentNumber, FraudulentDomain
from app.models.user import User
from app.schemas.reports import (
    ReportResponse,
    SMSReportCreate,
    EmailReportCreate,
    PhoneReportCreate,
)
from app.api.deps.auth_deps import get_current_user_optional
from typing import Optional

from datetime import datetime
import hashlib

router = APIRouter()


# === REPORT PHONE ===


@router.post("/report-phone", response_model=ReportResponse)
async def report_phone(
    report: PhoneReportCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Signaler un numéro frauduleux

    - Si 10+ signalements → auto-ajout dans fraudulent_numbers
    - Vérification communautaire

    **Accès:** Public (anonyme autorisé) / USER (authentifié)
    """

    user_id = str(current_user.user_id) if current_user else None

    content_hash = hashlib.sha256(report.phone.encode()).hexdigest()

    if user_id:
        existing = await db.execute(
            select(UserReport).where(
                UserReport.user_id == uuid.UUID(user_id),
                UserReport.content_hash == content_hash,
                UserReport.report_type == ReportType.CALL,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Vous avez déjà signalé ce numéro"
            )

    new_report = UserReport(
        user_id=uuid.UUID(user_id) if user_id else None,
        report_type=ReportType.CALL,
        content_hash=content_hash,
        phone_number=report.phone,
        verification_status=VerificationStatus.PENDING,
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    total_reports_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.content_hash == content_hash,
            UserReport.report_type == ReportType.CALL,
        )
    )
    total_reports = total_reports_result.scalar()

    verified = False
    auto_added = False

    if total_reports >= 10:
        await db.execute(
            update(UserReport)
            .where(UserReport.content_hash == content_hash)
            .values(
                verification_status=VerificationStatus.VERIFIED,
                verified_by=total_reports,
            )
        )

        existing_fraud = await db.execute(
            select(FraudulentNumber).where(
                FraudulentNumber.phone_number == report.phone
            )
        )
        fraud_entry = existing_fraud.scalar_one_or_none()

        if fraud_entry:
            fraud_entry.report_count += 1
            fraud_entry.last_reported = datetime.utcnow()
            fraud_entry.verified = True
        else:
            new_fraud = FraudulentNumber(
                phone_number=report.phone,
                country_code=report.country,
                fraud_type=report.fraud_type,
                confidence_score=min(0.7 + (total_reports * 0.02), 0.99),
                report_count=total_reports,
                verified=True,
                source="crowdsource",
            )
            db.add(new_fraud)
            auto_added = True

        await db.commit()
        verified = True

    return ReportResponse(
        success=True,
        report_id=str(new_report.report_id),
        message=f"Signalement enregistré. Total: {total_reports} signalement(s)",
        total_reports=total_reports,
        verified=verified,
        auto_added=auto_added,
    )


# === REPORT SMS ===
@router.post("/report-sms", response_model=ReportResponse)
async def report_sms(
    report: SMSReportCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Signaler un SMS frauduleux

    **Accès:** Public (anonyme autorisé) / USER (authentifié)
    """
    user_id = str(current_user.user_id) if current_user else None

    content_hash = hashlib.sha256(report.content.encode()).hexdigest()

    if user_id:
        existing = await db.execute(
            select(UserReport).where(
                UserReport.user_id == uuid.UUID(user_id),
                UserReport.content_hash == content_hash,
                UserReport.report_type == ReportType.SMS,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vous avez déjà signalé ce SMS")

    new_report = UserReport(
        user_id=uuid.UUID(user_id) if user_id else None,
        report_type=ReportType.SMS,
        content_hash=content_hash,
        reported_value=report.content[:100],
        fraud_category=report.fraud_category,
        comment=report.comment,
        verification_status=VerificationStatus.PENDING,
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    total_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.content_hash == content_hash,
            UserReport.report_type == ReportType.SMS,
        )
    )
    total_reports = total_result.scalar()

    verified = total_reports >= 5

    if verified:
        await db.execute(
            update(UserReport)
            .where(UserReport.content_hash == content_hash)
            .values(verification_status=VerificationStatus.VERIFIED)
        )
        await db.commit()

    return ReportResponse(
        success=True,
        report_id=str(new_report.report_id),
        message=f"SMS signalé. Total: {total_reports} signalement(s)",
        total_reports=total_reports,
        verified=verified,
    )


# === REPORT EMAIL ===


@router.post("/report-email", response_model=ReportResponse)
async def report_email(
    report: EmailReportCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Signaler un email/domaine frauduleux

    **Accès:** Public (anonyme autorisé) / USER (authentifié)
    """

    user_id = str(current_user.user_id) if current_user else None

    content_hash = hashlib.sha256(report.domain.encode()).hexdigest()

    if user_id:
        existing = await db.execute(
            select(UserReport).where(
                UserReport.user_id == uuid.UUID(user_id),
                UserReport.content_hash == content_hash,
                UserReport.report_type == ReportType.EMAIL,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Vous avez déjà signalé ce domaine"
            )

    new_report = UserReport(
        user_id=uuid.UUID(user_id) if user_id else None,
        report_type=ReportType.EMAIL,
        content_hash=content_hash,
        reported_value=report.domain,
        fraud_category=report.phishing_type,
        comment=report.comment,
        verification_status=VerificationStatus.PENDING,
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    total_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.content_hash == content_hash,
            UserReport.report_type == ReportType.EMAIL,
        )
    )
    total_reports = total_result.scalar()

    verified = False
    auto_added = False

    if total_reports >= 8:
        existing_domain = await db.execute(
            select(FraudulentDomain).where(FraudulentDomain.domain == report.domain)
        )
        domain_entry = existing_domain.scalar_one_or_none()

        if domain_entry:
            domain_entry.blocked_count += 1
        else:
            new_domain = FraudulentDomain(
                domain=report.domain,
                phishing_type=report.phishing_type,
                blocked_count=total_reports,
                reputation_score=min(0.7 + (total_reports * 0.03), 0.99),
            )
            db.add(new_domain)
            auto_added = True

        await db.commit()
        verified = True

    return ReportResponse(
        success=True,
        report_id=str(new_report.report_id),
        message=f"Email signalé. Total: {total_reports} signalement(s)",
        total_reports=total_reports,
        verified=verified,
        auto_added=auto_added,
    )


# === GET REPORT STATS ===


@router.get("/stats")
async def get_report_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Statistiques des signalements

    - Si authentifié: Statistiques personnelles
    - Si anonyme: Statistiques globales uniquement

    **Accès:** Public / USER
    """

    total_reports_result = await db.execute(select(func.count(UserReport.report_id)))
    total_reports = total_reports_result.scalar()

    verified_reports_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.verification_status == VerificationStatus.VERIFIED
        )
    )
    verified_reports = verified_reports_result.scalar()

    response = {
        "total_reports": total_reports,
        "verified_reports": verified_reports,
        "pending_reports": total_reports - verified_reports,
    }

    if current_user:
        user_reports_result = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.user_id == current_user.user_id
            )
        )
        user_reports = user_reports_result.scalar()

        user_verified_result = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.user_id == current_user.user_id,
                UserReport.verification_status == VerificationStatus.VERIFIED,
            )
        )
        user_verified = user_verified_result.scalar()

        response["user_stats"] = {
            "user_id": str(current_user.user_id),
            "total_reports": user_reports,
            "verified_reports": user_verified,
            "contribution_score": user_verified * 10,
        }

    return response
