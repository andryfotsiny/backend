from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import time
from app.models.fraud import FraudulentNumber, FraudulentDomain
from app.models.report import DetectionLog
from app.services.cache import cache_service
from app.services.ml_service import ml_service
from app.services.rag_service import rag_service
from app.rag.embeddings import embedding_service
from sqlalchemy.exc import SQLAlchemyError
import logging


class DetectionService:
    async def check_phone(
        self, db: AsyncSession, phone: str, country: str, user_id: Optional[str] = None
    ) -> dict:
        start_time = time.time()

        cache_key = f"phone:{phone}"
        cached = await cache_service.get(cache_key)
        if cached:
            return {
                **cached,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }

        result = await db.execute(
            select(FraudulentNumber).where(FraudulentNumber.phone_number == phone)
        )
        fraud_entry = result.scalar_one_or_none()

        if fraud_entry:
            response = {
                "is_fraud": True,
                "confidence": fraud_entry.confidence_score,
                "category": fraud_entry.fraud_type.value,
                "reason": f"Signalé {fraud_entry.report_count} fois",
                "action": "block",
                "similar_cases": fraud_entry.report_count,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }
            await cache_service.set(cache_key, response, expire=7200)
            await self._log_detection(
                db, user_id, "phone", True,
                fraud_entry.confidence_score, "blacklist",
                int((time.time() - start_time) * 1000),
                meta_data={"phone": phone, "country": country},
            )
            return response

        is_fraud, confidence = ml_service.predict_phone(
            phone, {"hour": 14, "call_count": 1}
        )

        response = {
            "is_fraud": is_fraud,
            "confidence": confidence,
            "category": "suspected_scam" if is_fraud else None,
            "reason": "Analyse ML" if is_fraud else "Numéro non signalé",
            "action": "block" if is_fraud else "allow",
            "similar_cases": 0,
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        await cache_service.set(cache_key, response, expire=3600)
        await self._log_detection(
            db, user_id, "phone", is_fraud, confidence, "ml",
            int((time.time() - start_time) * 1000),
            meta_data={"phone": phone, "country": country},
        )

        return response

    async def check_sms(
        self, db: AsyncSession, content: str, sender: str, user_id: Optional[str] = None
    ) -> dict:
        start_time = time.time()

        is_fraud, confidence, risk_factors = ml_service.predict_sms(content, sender)

        if confidence < 0.8:
            vector = embedding_service.get_embedding(content)
            if vector:
                rag_fraud, similar_count = rag_service.check_similarity_fraud(vector)
                if rag_fraud:
                    is_fraud = True
                    confidence = max(confidence, 0.9)
                    risk_factors.append(f"{similar_count} cas similaires signalés")

        response = {
            "is_fraud": is_fraud,
            "confidence": confidence,
            "category": "phishing" if is_fraud else None,
            "risk_factors": risk_factors,
            "action": "block_link" if is_fraud else "allow",
            "similar_frauds": 0,
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        await self._log_detection(
            db, user_id, "sms", is_fraud, confidence, "ml_rag",
            int((time.time() - start_time) * 1000),
            meta_data={
                "content": content[:500],
                "sender": sender,
                "category": "phishing" if is_fraud else "unknown",
            },
        )

        return response

    async def check_email(
        self,
        db: AsyncSession,
        sender: str,
        subject: str,
        body: str,
        user_id: Optional[str] = None,
    ) -> dict:
        start_time = time.time()

        domain = sender.split("@")[1] if "@" in sender else ""

        result = await db.execute(
            select(FraudulentDomain).where(FraudulentDomain.domain == domain)
        )
        fraud_domain = result.scalar_one_or_none()

        if fraud_domain:
            response = {
                "is_fraud": True,
                "confidence": fraud_domain.reputation_score,
                "phishing_type": fraud_domain.phishing_type,
                "risk_factors": ["Domaine signalé comme frauduleux"],
                "sender_verified": False,
                "spf_valid": fraud_domain.spf_valid,
                "dkim_valid": fraud_domain.dkim_valid,
                "action": "block",
                "response_time_ms": int((time.time() - start_time) * 1000),
            }
            await self._log_detection(
                db, user_id, "email", True,
                fraud_domain.reputation_score, "blacklist",
                int((time.time() - start_time) * 1000),
                meta_data={
                    "sender": sender,
                    "subject": subject,
                    "has_attachment": False,
                },
            )
            return response

        is_fraud, confidence = ml_service.predict_email(sender, subject, body)

        response = {
            "is_fraud": is_fraud,
            "confidence": confidence,
            "phishing_type": "suspected" if is_fraud else None,
            "risk_factors": ["Contenu suspect"] if is_fraud else [],
            "sender_verified": False,
            "spf_valid": False,
            "dkim_valid": False,
            "action": "warn" if is_fraud else "allow",
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        await self._log_detection(
            db, user_id, "email", is_fraud, confidence, "ml",
            int((time.time() - start_time) * 1000),
            meta_data={
                "sender": sender,
                "subject": subject,
                "has_attachment": False,
            },
        )

        return response

    async def _log_detection(
        self,
        db: AsyncSession,
        user_id: Optional[str],
        detection_type: str,
        is_fraud: bool,
        confidence: float,
        method: str,
        response_time: int,
        meta_data: Optional[dict] = None,
    ):
        try:
            log = DetectionLog(
                user_id=user_id,
                detection_type=detection_type,
                is_fraud=is_fraud,
                confidence=confidence,
                method_used=method,
                response_time_ms=response_time,
                model_version="1.0",
                meta_data=meta_data or {},
            )
            db.add(log)
            await db.commit()
        except SQLAlchemyError as e:
            logging.exception("Failed to log detection: %s", e)
            await db.rollback()


detection_service = DetectionService()