import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.session import get_db
from app.models.report import UserReport, VerificationStatus, ReportType
from app.models.fraud import FraudulentNumber, FraudType, FraudulentDomain
from app.schemas.reports import ReportResponse, SMSReportCreate, EmailReportCreate, PhoneReportCreate

from datetime import datetime
import hashlib

router = APIRouter()

# === SCHEMAS ===




# === ENDPOINTS ===

@router.post("/report-phone", response_model=ReportResponse)
async def report_phone(
    report: PhoneReportCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Signaler un numéro frauduleux

    - Si 10+ signalements → auto-ajout dans fraudulent_numbers
    - Vérification communautaire
    """

    # 1. Créer hash du contenu
    content_hash = hashlib.sha256(report.phone.encode()).hexdigest()

    # 2. Vérifier si déjà signalé par cet utilisateur
    if report.user_id:
        existing = await db.execute(
            select(UserReport).where(
                UserReport.user_id == report.user_id,
                UserReport.content_hash == content_hash,
                UserReport.report_type == ReportType.CALL
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vous avez déjà signalé ce numéro")

    # 3. Créer le signalement
    new_report = UserReport(
        user_id=uuid.UUID(report.user_id) if report.user_id else None,
        report_type=ReportType.CALL,
        content_hash=content_hash,
        phone_number=report.phone,
        verification_status=VerificationStatus.PENDING
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    # 4. Compter total signalements pour ce numéro
    total_reports_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.content_hash == content_hash,
            UserReport.report_type == ReportType.CALL
        )
    )
    total_reports = total_reports_result.scalar()

    # 5. Auto-vérification si 10+ signalements
    verified = False
    auto_added = False

    if total_reports >= 10:
        # Marquer comme vérifié
        await db.execute(
            update(UserReport)
            .where(UserReport.content_hash == content_hash)
            .values(
                verification_status=VerificationStatus.VERIFIED,
                verified_by=total_reports
            )
        )

        # Vérifier si déjà dans fraudulent_numbers
        existing_fraud = await db.execute(
            select(FraudulentNumber).where(
                FraudulentNumber.phone_number == report.phone
            )
        )
        fraud_entry = existing_fraud.scalar_one_or_none()

        if fraud_entry:
            # Incrémenter report_count
            fraud_entry.report_count += 1
            fraud_entry.last_reported = datetime.utcnow()
            fraud_entry.verified = True
        else:
            # Ajouter nouveau numéro frauduleux
            new_fraud = FraudulentNumber(
                phone_number=report.phone,
                country_code=report.country,
                fraud_type=report.fraud_type,
                confidence_score=min(0.7 + (total_reports * 0.02), 0.99),
                report_count=total_reports,
                verified=True,
                source="crowdsource"
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
        auto_added=auto_added
    )


@router.post("/report-sms", response_model=ReportResponse)
async def report_sms(
    report: SMSReportCreate,
    db: AsyncSession = Depends(get_db)
):
    """Signaler un SMS frauduleux"""

    # Hash contenu
    content_hash = hashlib.sha256(report.content.encode()).hexdigest()

    # Créer signalement
    new_report = UserReport(
        user_id=report.user_id or "anonymous",
        report_type=ReportType.SMS,
        content_hash=content_hash,
        reported_value=report.content[:100],
        fraud_category=report.fraud_category,
        comment=report.comment,
        verification_status=VerificationStatus.PENDING
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    # Compter signalements
    total_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.content_hash == content_hash,
            UserReport.report_type == ReportType.SMS
        )
    )
    total_reports = total_result.scalar()

    # Auto-vérification
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
        verified=verified
    )


@router.post("/report-email", response_model=ReportResponse)
async def report_email(
    report: EmailReportCreate,
    db: AsyncSession = Depends(get_db)
):
    """Signaler un email/domaine frauduleux"""

    content_hash = hashlib.sha256(report.domain.encode()).hexdigest()

    new_report = UserReport(
        user_id=report.user_id or "anonymous",
        report_type=ReportType.EMAIL,
        content_hash=content_hash,
        reported_value=report.domain,
        fraud_category=report.phishing_type,
        comment=report.comment,
        verification_status=VerificationStatus.PENDING
    )

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    total_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.content_hash == content_hash,
            UserReport.report_type == ReportType.EMAIL
        )
    )
    total_reports = total_result.scalar()

    verified = False
    auto_added = False

    # Auto-ajout domaine si 8+ signalements
    if total_reports >= 8:
        existing_domain = await db.execute(
            select(FraudulentDomain).where(
                FraudulentDomain.domain == report.domain
            )
        )
        domain_entry = existing_domain.scalar_one_or_none()

        if domain_entry:
            domain_entry.blocked_count += 1
        else:
            new_domain = FraudulentDomain(
                domain=report.domain,
                phishing_type=report.phishing_type,
                blocked_count=total_reports,
                reputation_score=min(0.7 + (total_reports * 0.03), 0.99)
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
        auto_added=auto_added
    )

@router.get("/stats")
async def get_report_stats(db: AsyncSession = Depends(get_db)):
    """Statistiques des signalements"""

    total_reports_result = await db.execute(select(func.count(UserReport.report_id)))
    total_reports = total_reports_result.scalar()

    verified_reports_result = await db.execute(
        select(func.count(UserReport.report_id)).where(
            UserReport.verification_status == VerificationStatus.VERIFIED
        )
    )
    verified_reports = verified_reports_result.scalar()

    return {
        "total_reports": total_reports,
        "verified_reports": verified_reports,
        "pending_reports": total_reports - verified_reports
    }