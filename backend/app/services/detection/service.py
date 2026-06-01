# app/services/detection/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import time
from datetime import datetime, timezone

def _now() -> datetime:
    """Retourne l'heure UTC actuelle (compatible Python 3.12+)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
from app.models.fraud import FraudulentNumber, FraudulentDomain, FraudType
from app.models.business import Business
from app.models.report import DetectionLog
from app.services.cache import cache_service
from app.services.ml_service import ml_service
from app.services.rag_service import rag_service
from app.rag.embeddings import embedding_service
from sqlalchemy.exc import SQLAlchemyError
from app.core.phone_utils import normalize_phone_number
from app.core.telemarketing import is_telemarketing_number, TELEMARKETING_RESPONSE
from app.core.trusted_domains import (
    is_trusted_email_domain,
    is_trusted_sms_sender,
)
import logging
import dns.resolver


class DetectionService:
    async def check_phone(
        self, db: AsyncSession, phone: str, country: str, user_id: Optional[str] = None
    ) -> dict:
        start_time = time.time()

        normalized_phone = normalize_phone_number(phone, country)
        cache_key = f"phone:{normalized_phone}"
        cached = await cache_service.get(cache_key)
        if cached:
            return {
                **cached,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }

        # 1. Blacklist DB
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
                "status": "blacklist",
                "business": None,
            }
            await cache_service.set(cache_key, response, expire=7200)
            await self._log_detection(
                db, user_id, "phone", True,
                confidence=fraud_entry.confidence_score,
                method="blacklist",
                response_time=int((time.time() - start_time) * 1000),
                meta_data={"phone": normalized_phone, "country": country},
            )
            return response

        # 1.5. Télémarketing (check en mémoire, pas de DB)
        if is_telemarketing_number(normalized_phone, country):
            response = {
                **TELEMARKETING_RESPONSE,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }
            await cache_service.set(cache_key, response, expire=86400)
            await self._log_detection(
                db, user_id, "phone", True,
                confidence=0.6,
                method="telemarketing",
                response_time=int((time.time() - start_time) * 1000),
                meta_data={"phone": normalized_phone, "country": country},
            )
            return response

        # 2. Business (whitelist)
        digits_only = "".join(filter(str.isdigit, phone))
        normalized_digits = normalized_phone.lstrip("+")

        business_result = await db.execute(
            select(Business).where(
                Business.tel.in_([normalized_phone, normalized_digits, phone, digits_only])
            )
        )
        business_entry = business_result.scalar_one_or_none()

        if business_entry:
            business_profile = {
                "id": business_entry.id,
                "nomination": business_entry.nomination,
                "nom": business_entry.nom,
                "adresse": business_entry.adresse,
                "ville": business_entry.ville,
                "code_postale": business_entry.code_postale,
                "prefixe": business_entry.prefixe,
                "code_pays": business_entry.code_pays,
                "tel": business_entry.tel,
                "act": business_entry.act,
                "created_at": business_entry.created_at.isoformat() if business_entry.created_at else None,
            }
            response = {
                "is_fraud": False,
                "confidence": 0.0,
                "category": None,
                "reason": "Numéro appartenant à un business enregistré",
                "action": "allow",
                "similar_cases": 0,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "status": "business",
                "business": business_profile,
            }
            await cache_service.set(cache_key, response, expire=3600)
            await self._log_detection(
                db, user_id, "phone", False,
                confidence=0.0, method="business",
                response_time=int((time.time() - start_time) * 1000),
                meta_data={"phone": normalized_phone, "country": country},
            )
            return response

        # 3. ML — features basées sur le contexte réel
        current_hour = _now().hour
        is_fraud, confidence = ml_service.predict_phone(
            normalized_phone, {"hour": current_hour, "call_count": 1}
        )

        response = {
            "is_fraud": is_fraud,
            "confidence": confidence,
            "category": "suspected_scam" if is_fraud else None,
            "reason": "Analyse ML" if is_fraud else "Numéro non signalé",
            "action": "block" if is_fraud else "allow",
            "similar_cases": 0,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "status": "blacklist" if is_fraud else "unknown",
            "business": None,
        }

        await cache_service.set(cache_key, response, expire=3600)
        await self._log_detection(
            db, user_id, "phone", is_fraud, confidence, "ml",
            int((time.time() - start_time) * 1000),
            meta_data={"phone": normalized_phone, "country": country},
        )

        return response

    async def check_sms(
        self, db: AsyncSession, content: str, sender: str, user_id: Optional[str] = None
    ) -> dict:
        start_time = time.time()

        if is_trusted_sms_sender(sender):
            try:
                ml_is_fraud, ml_confidence, _ = ml_service.predict_sms(content, sender)
            except Exception:
                ml_is_fraud, ml_confidence = False, 0.0

            if ml_is_fraud and ml_confidence > 0.85:
                action = "warn"
                risk_factors = [
                    "Expéditeur de confiance mais contenu inhabituel",
                    "Vérifiez les liens avant de cliquer",
                ]
                category = "suspicious_content"
            else:
                action = "allow"
                risk_factors = []
                category = None

            response = {
                "is_fraud": False,
                "confidence": 0.0,
                "category": category,
                "risk_factors": risk_factors,
                "action": action,
                "similar_frauds": 0,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }

            await self._log_detection(
                db, user_id, "sms", False,
                confidence=0.0, method="whitelist",
                response_time=int((time.time() - start_time) * 1000),
                meta_data={
                    "content": content[:500],
                    "sender": sender,
                    "category": category or "legitimate",
                    "trusted_sender": True,
                },
            )
            return response

        similar_frauds_count = 0
        similar_examples = []
        rag_is_fraud = False
        rag_confidence = 0.0

        if embedding_service.enabled and rag_service.enabled:
            try:
                vector = embedding_service.get_embedding(content)
                if vector:
                    similar_results = rag_service.search_similar(vector, limit=10)
                    high_similarity = [r for r in similar_results if r["score"] >= 0.85]
                    similar_frauds_count = len(high_similarity)

                    similar_examples = [
                        {
                            "score": round(r["score"], 3),
                            "preview": str(r["payload"].get("content", ""))[:100],
                            "category": r["payload"].get("fraud_category"),
                        }
                        for r in high_similarity[:3]
                    ]

                    if similar_frauds_count >= 2:
                        rag_is_fraud = True
                        rag_confidence = float(high_similarity[0]["score"])
            except Exception as e:
                logging.warning("RAG similarity search failed: %s", e)

        try:
            ml_is_fraud, ml_confidence, ml_risk_factors = ml_service.predict_sms(content, sender)
        except Exception as e:
            logging.error("ML prediction failed: %s", e)
            ml_is_fraud, ml_confidence, ml_risk_factors = False, 0.0, []

        is_fraud = ml_is_fraud or rag_is_fraud
        confidence = max(ml_confidence, rag_confidence)

        risk_factors = list(ml_risk_factors) if ml_risk_factors else []
        if rag_is_fraud:
            risk_factors.append(
                f"Similaire à {similar_frauds_count} SMS frauduleux déjà signalés"
            )

        if rag_is_fraud and ml_is_fraud:
            method = "ml_rag"
        elif rag_is_fraud:
            method = "rag"
        else:
            method = "ml"

        if is_fraud:
            try:
                normalized_sender = normalize_phone_number(sender)
                result_fn = await db.execute(
                    select(FraudulentNumber).where(FraudulentNumber.phone_number == normalized_sender)
                )
                existing_fn = result_fn.scalar_one_or_none()

                if existing_fn:
                    existing_fn.report_count += 1
                    existing_fn.last_reported = _now()
                    if confidence > existing_fn.confidence_score:
                        existing_fn.confidence_score = confidence
                else:
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
                        report_count=1,
                    )
                    db.add(new_fn)
                await db.commit()
            except Exception as e:
                logging.exception("Failed to auto-report fraudulent SMS sender: %s", e)
                await db.rollback()

        if is_fraud and confidence >= 0.85 and embedding_service.enabled and rag_service.enabled:
            try:
                vector = embedding_service.get_embedding(content)
                if vector:
                    rag_service.add_vector(
                        vector=vector,
                        payload={
                            "content": content[:500],
                            "type": "sms_scam",
                            "fraud_category": "phishing",
                            "sender": sender,
                            "confidence": confidence,
                            "source": method,
                            "timestamp": _now().isoformat(),
                        },
                    )
            except Exception as e:
                logging.warning("Failed to add SMS to RAG vector DB: %s", e)

        response = {
            "is_fraud": is_fraud,
            "confidence": float(confidence),
            "category": "phishing" if is_fraud else None,
            "risk_factors": risk_factors,
            "action": "block_link" if is_fraud else "allow",
            "similar_frauds": similar_frauds_count,
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        await self._log_detection(
            db, user_id, "sms", is_fraud, confidence, method,
            int((time.time() - start_time) * 1000),
            meta_data={
                "content": content[:500],
                "sender": sender,
                "category": "phishing" if is_fraud else "unknown",
                "similar_examples": similar_examples,
                "rag_hit": rag_is_fraud,
                "ml_hit": ml_is_fraud,
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
        domain = domain.strip().lower()

        if is_trusted_email_domain(domain):
            try:
                ml_is_fraud, ml_confidence = ml_service.predict_email(sender, subject, body)
            except Exception:
                ml_is_fraud, ml_confidence = False, 0.0

            if ml_is_fraud and ml_confidence > 0.85:
                action = "warn"
                risk_factors = [
                    "Expéditeur de confiance mais contenu inhabituel",
                    "Vérifiez l'authenticité avant toute action",
                ]
                phishing_type = "suspicious_content"
            else:
                action = "allow"
                risk_factors = []
                phishing_type = None

            response = {
                "is_fraud": False,
                "confidence": 0.0,
                "phishing_type": phishing_type,
                "risk_factors": risk_factors,
                "sender_verified": True,
                "spf_valid": True,
                "dkim_valid": True,
                "action": action,
                "response_time_ms": int((time.time() - start_time) * 1000),
            }

            await self._log_detection(
                db, user_id, "email", False,
                confidence=0.0, method="whitelist",
                response_time=int((time.time() - start_time) * 1000),
                meta_data={
                    "sender": sender,
                    "subject": subject,
                    "has_attachment": False,
                    "trusted_domain": True,
                },
            )
            return response

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
                meta_data={"sender": sender, "subject": subject, "has_attachment": False},
            )
            return response

        similar_frauds_count = 0
        rag_is_fraud = False
        rag_confidence = 0.0
        combined_text = f"{subject} {body}"

        if embedding_service.enabled and rag_service.enabled:
            try:
                vector = embedding_service.get_embedding(combined_text)
                if vector:
                    similar_results = rag_service.search_similar(vector, limit=10)
                    high_similarity = [r for r in similar_results if r["score"] >= 0.85]
                    similar_frauds_count = len(high_similarity)

                    if similar_frauds_count >= 2:
                        rag_is_fraud = True
                        rag_confidence = float(high_similarity[0]["score"])
            except Exception as e:
                logging.warning("RAG similarity search failed for email: %s", e)

        try:
            ml_is_fraud, ml_confidence = ml_service.predict_email(sender, subject, body)
        except Exception as e:
            logging.error("Email ML prediction failed: %s", e)
            ml_is_fraud, ml_confidence = False, 0.0

        spf_valid = False
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            for rdata in answers:
                if "v=spf1" in str(rdata):
                    spf_valid = True
                    break
        except Exception:
            spf_valid = False

        is_fraud = ml_is_fraud or rag_is_fraud
        confidence = max(ml_confidence, rag_confidence)

        risk_factors = []
        if ml_is_fraud:
            risk_factors.append("Contenu suspect (ML)")
        if rag_is_fraud:
            risk_factors.append(f"Similaire à {similar_frauds_count} emails frauduleux signalés")
        if not spf_valid:
            risk_factors.append("Absence de protection SPF sur le domaine")

        if rag_is_fraud and ml_is_fraud:
            method = "ml_rag"
        elif rag_is_fraud:
            method = "rag"
        else:
            method = "ml"

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
                        blocked_count=1,
                    )
                    db.add(new_fd)
                await db.commit()
            except Exception as e:
                logging.exception("Failed to auto-report fraudulent email domain: %s", e)
                await db.rollback()

        if is_fraud and confidence >= 0.85 and embedding_service.enabled and rag_service.enabled:
            try:
                vector = embedding_service.get_embedding(combined_text)
                if vector:
                    rag_service.add_vector(
                        vector=vector,
                        payload={
                            "content": combined_text[:500],
                            "type": "email_scam",
                            "fraud_category": "phishing",
                            "sender": sender,
                            "domain": domain,
                            "confidence": confidence,
                            "source": method,
                            "timestamp": _now().isoformat(),
                        },
                    )
            except Exception as e:
                logging.warning("Failed to add email to RAG vector DB: %s", e)

        response = {
            "is_fraud": is_fraud,
            "confidence": float(confidence),
            "phishing_type": "suspected" if is_fraud else None,
            "risk_factors": risk_factors,
            "sender_verified": spf_valid,
            "spf_valid": spf_valid,
            "dkim_valid": False,
            "action": "warn" if (is_fraud or not spf_valid) else "allow",
            "response_time_ms": int((time.time() - start_time) * 1000),
        }

        await self._log_detection(
            db, user_id, "email", is_fraud, confidence, method,
            int((time.time() - start_time) * 1000),
            meta_data={
                "sender": sender,
                "subject": subject,
                "has_attachment": False,
                "rag_hit": rag_is_fraud,
                "ml_hit": ml_is_fraud,
                "similar_count": similar_frauds_count,
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