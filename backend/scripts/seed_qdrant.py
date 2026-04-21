"""
Script de peuplement de Qdrant avec les SMS et emails frauduleux déjà signalés.

À exécuter une seule fois après avoir activé le RAG, pour bootstraper
la base vectorielle avec les données historiques.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.seed_qdrant
"""

import asyncio
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.report import UserReport, ReportType, VerificationStatus
from app.services.rag_service import rag_service
from app.rag.embeddings import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_qdrant():
    """Charge tous les reports vérifiés dans Qdrant."""

    # 1. Initialiser les services
    logger.info("Initializing RAG service...")
    rag_service.connect()
    if not rag_service.enabled:
        logger.error("❌ Qdrant unavailable, cannot seed.")
        return

    logger.info("Loading embedding model (peut prendre ~30s)...")
    embedding_service.load_model()
    if not embedding_service.enabled:
        logger.error("❌ Embedding model unavailable, cannot seed.")
        return

    # 2. Lire les reports vérifiés
    async with AsyncSessionLocal() as db:
        logger.info("Loading verified SMS reports from DB...")

        sms_query = select(UserReport).where(
            UserReport.report_type == ReportType.SMS,
            UserReport.verification_status == VerificationStatus.VERIFIED,
        )
        sms_result = await db.execute(sms_query)
        sms_reports = sms_result.scalars().all()
        logger.info(f"Found {len(sms_reports)} verified SMS reports")

        email_query = select(UserReport).where(
            UserReport.report_type == ReportType.EMAIL,
            UserReport.verification_status == VerificationStatus.VERIFIED,
        )
        email_result = await db.execute(email_query)
        email_reports = email_result.scalars().all()
        logger.info(f"Found {len(email_reports)} verified email reports")

    # 3. Indexer les SMS dans Qdrant
    sms_added = 0
    sms_skipped = 0
    for report in sms_reports:
        content = report.reported_value or ""
        if not content or len(content) < 10:
            sms_skipped += 1
            continue

        try:
            vector = embedding_service.get_embedding(content)
            if not vector:
                sms_skipped += 1
                continue

            rag_service.add_vector(
                vector=vector,
                payload={
                    "content": content[:500],
                    "type": "sms_scam",
                    "fraud_category": report.fraud_category or "unknown",
                    "verified": True,
                    "source": "historical_report",
                    "report_id": str(report.report_id),
                    "timestamp": report.timestamp.isoformat() if report.timestamp else None,
                },
            )
            sms_added += 1
            if sms_added % 10 == 0:
                logger.info(f"  ... {sms_added} SMS indexed")
        except Exception as e:
            logger.warning(f"Failed to index SMS report {report.report_id}: {e}")
            sms_skipped += 1

    # 4. Indexer les emails dans Qdrant
    email_added = 0
    email_skipped = 0
    for report in email_reports:
        content = report.reported_value or ""
        if report.comment:
            content = f"{content} {report.comment}"
        if not content or len(content) < 10:
            email_skipped += 1
            continue

        try:
            vector = embedding_service.get_embedding(content)
            if not vector:
                email_skipped += 1
                continue

            rag_service.add_vector(
                vector=vector,
                payload={
                    "content": content[:500],
                    "type": "email_scam",
                    "fraud_category": report.fraud_category or "unknown",
                    "verified": True,
                    "source": "historical_report",
                    "report_id": str(report.report_id),
                    "timestamp": report.timestamp.isoformat() if report.timestamp else None,
                },
            )
            email_added += 1
            if email_added % 10 == 0:
                logger.info(f"  ... {email_added} emails indexed")
        except Exception as e:
            logger.warning(f"Failed to index email report {report.report_id}: {e}")
            email_skipped += 1

    # 5. Récap
    logger.info("=" * 60)
    logger.info("✅ SEEDING TERMINÉ")
    logger.info(f"   SMS indexed:    {sms_added} (skipped: {sms_skipped})")
    logger.info(f"   Emails indexed: {email_added} (skipped: {email_skipped})")
    logger.info(f"   Total vectors:  {sms_added + email_added}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_qdrant())