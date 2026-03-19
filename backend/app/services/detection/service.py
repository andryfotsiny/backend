from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import time
from datetime import datetime
from app.models.fraud import FraudulentNumber, FraudulentDomain, FraudType
from app.models.report import DetectionLog
from app.services.cache import cache_service
from app.services.ml_service import ml_service
from sqlalchemy.exc import SQLAlchemyError
from app.core.phone_utils import normalize_phone_number
import logging
import dns.resolver


class DetectionService:
    async def check_phone(
        self, db: AsyncSession, phone: str, country: str, user_id: Optional[str] = None
    ) -> dict:
        start_time = time.time()

        # Normalisation
        normalized_phone = normalize_phone_number(phone, country)
        cache_key = f"phone:{normalized_phone}"
        cached = await cache_service.get(cache_key)
        if cached:
            return {
                **cached,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }

        result = await db.execute(
            select(FraudulentNumber).where(FraudulentNumber.phone_number == normalized_phone)
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
                db,
                user_id,
                "phone",
                True,
                confidence=fraud_entry.confidence_score,
                method="blacklist",
                response_time=int((time.time() - start_time) * 1000),
                meta_data={"phone": normalized_phone, "country": country},
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
            db,
            user_id,
            "phone",
            is_fraud,
            confidence,
            "ml",
            int((time.time() - start_time) * 1000),
            meta_data={"phone": normalized_phone, "country": country},
        )

        return response

    async def check_sms(
        self, db: AsyncSession, content: str, sender: str, user_id: Optional[str] = None
    ) -> dict:
        start_time = time.time()

        is_fraud, confidence, risk_factors = ml_service.predict_sms(content, sender)

        if is_fraud:
            try:
                normalized_sender = normalize_phone_number(sender)
                result_fn = await db.execute(
                    select(FraudulentNumber).where(FraudulentNumber.phone_number == normalized_sender)
                )
                existing_fn = result_fn.scalar_one_or_none()

                if existing_fn:
                    existing_fn.report_count += 1
                    existing_fn.last_reported = datetime.utcnow()
                    if confidence > existing_fn.confidence_score:
                        existing_fn.confidence_score = confidence
                else:
                    # Try to extract country from phone if parsed, else default to MG
                    country_code = "MG"
                    try:
                        import phonenumbers
                        parsed_sender = phonenumbers.parse(sender, "MG")
                        country_code = phonenumbers.region_code_for_number(parsed_sender) or "MG"
                    except Exception:
                        pass

                    new_fn = FraudulentNumber(
                        phone_number=normalized_sender,
                        country_code=country_code,
                        fraud_type=FraudType.PHISHING,
                        confidence_score=confidence,
                        source="ai_detection",
                        report_count=1
                    )
                    db.add(new_fn)
                await db.commit()
            except Exception as e:
                logging.exception("Failed to auto-report fraudulent SMS sender: %s", e)
                await db.rollback()

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
            db,
            user_id,
            "sms",
            is_fraud,
            confidence,
            "ml_rag",
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
                db,
                user_id,
                "email",
                True,
                fraud_domain.reputation_score,
                "blacklist",
                int((time.time() - start_time) * 1000),
                meta_data={
                    "sender": sender,
                    "subject": subject,
                    "has_attachment": False,
                },
            )
            return response

        is_fraud, confidence = ml_service.predict_email(sender, subject, body)

        spf_valid = False
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            for rdata in answers:
                if "v=spf1" in str(rdata):
                    spf_valid = True
                    break
        except Exception:
            spf_valid = False

        if is_fraud:
            try:
                result_fd = await db.execute(
                    select(FraudulentDomain).where(FraudulentDomain.domain == domain)
                )
                existing_fd = result_fd.scalar_one_or_none()

                if existing_fd:
                    existing_fd.blocked_count += 1
                    if confidence > existing_fd.reputation_score:
                        existing_fd.reputation_score = confidence
                else:
                    new_fd = FraudulentDomain(
                        domain=domain,
                        phishing_type="suspected",
                        spf_valid=spf_valid,
                        dkim_valid=False,
                        reputation_score=confidence,
                        blocked_count=1
                    )
                    db.add(new_fd)
                await db.commit()
            except Exception as e:
                logging.exception("Failed to auto-report fraudulent email domain: %s", e)
                await db.rollback()

        response = {
            "is_fraud": is_fraud,
            "confidence": confidence,
            "phishing_type": "suspected" if is_fraud else None,
            "risk_factors": ["Contenu suspect"] if is_fraud else [],
            "sender_verified": spf_valid,
            "spf_valid": spf_valid,
            "dkim_valid": False,
            "action": "warn" if is_fraud or not spf_valid else "allow",
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        if not spf_valid:
            response["risk_factors"].append("Absence de protection SPF sur le domaine")

        await self._log_detection(
            db,
            user_id,
            "email",
            is_fraud,
            confidence,
            "ml",
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
