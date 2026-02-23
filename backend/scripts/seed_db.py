import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session_maker
from app.models.fraud import FraudulentNumber, FraudulentSMSPattern, FraudulentDomain, FraudType
from app.models.user import User, UserRole
from app.services.auth_service import auth_service
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select

async def seed_database():
    async with async_session_maker() as session:

        # ═══════════════════════════════════════════════════════════
        # 1. CRÉER COMPTE ORGANISATION PAR DÉFAUT
        # ═══════════════════════════════════════════════════════════

        email = "admin@dyleth.com"
        phone = "+261340000000"
        password = "Admin@2026"

        result = await session.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            email_hash = hashlib.sha256(email.encode()).hexdigest()
            phone_hash = hashlib.sha256(phone.encode()).hexdigest()
            password_hash = auth_service.hash_password(password)

            admin_user = User(
                email=email,
                phone=phone,
                email_hash=email_hash,
                phone_hash=phone_hash,
                password_hash=password_hash,
                role=UserRole.ADMIN,
                country_code="MG",
                settings={
                    "theme": "light",
                    "language": "fr",
                    "notifications": True,
                    "auto_block": True
                },
                device_tokens=[],
                report_count=0,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                last_active=datetime.now(timezone.utc).replace(tzinfo=None)
            )

            session.add(admin_user)
            await session.commit()
            print("✅ Compte ADMIN créé")
        else:
            # Mettre à jour le hash et forcer le rôle ADMIN pour l'utilisateur existant
            existing_user.password_hash = auth_service.hash_password(password)
            existing_user.role = UserRole.ADMIN
            existing_user.last_active = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()
            print("✅ Compte ADMIN existant mis à jour (Rôle ADMIN + Hash Argon2)")
        
        print(f"   Email: {email}")
        print(f"   Password: {password}")

        # ═══════════════════════════════════════════════════════════
        # 2. FRAUDULENT NUMBERS
        # ═══════════════════════════════════════════════════════════

        existing = (await session.execute(select(FraudulentNumber))).scalars().first()
        if not existing:
            fraud_numbers = [
                FraudulentNumber(
                    phone_number="+33756123456",
                    country_code="FR",
                    fraud_type=FraudType.SCAM,
                    confidence_score=0.95,
                    report_count=127,
                    verified=True,
                    source="crowdsource"
                ),
                FraudulentNumber(
                    phone_number="+33698765432",
                    country_code="FR",
                    fraud_type=FraudType.SPAM,
                    confidence_score=0.88,
                    report_count=45,
                    verified=True,
                    source="crowdsource"
                ),
                FraudulentNumber(
                    phone_number="+14155551234",
                    country_code="US",
                    fraud_type=FraudType.ROBOCALL,
                    confidence_score=0.92,
                    report_count=89,
                    verified=True,
                    source="partner"
                ),
                FraudulentNumber(
                    phone_number="+261340000001",
                    country_code="MG",
                    fraud_type=FraudType.SCAM,
                    confidence_score=0.87,
                    report_count=23,
                    verified=True,
                    source="crowdsource"
                ),
            ]
            session.add_all(fraud_numbers)
            await session.commit()
            print(f"✅ {len(fraud_numbers)} fraudulent numbers insérés")
        else:
            print("✅ Fraudulent numbers existent déjà, skip")

        # ═══════════════════════════════════════════════════════════
        # 3. SMS PATTERNS
        # ═══════════════════════════════════════════════════════════

        existing = (await session.execute(select(FraudulentSMSPattern))).scalars().first()
        if not existing:
            sms_patterns = [
                FraudulentSMSPattern(
                    keywords=["urgent", "payez", "maintenant", "cliquez"],
                    fraud_category="phishing_livraison",
                    language="fr",
                    severity=8,
                    detection_count=234
                ),
                FraudulentSMSPattern(
                    keywords=["compte", "bloqué", "confirmer", "identifiants"],
                    fraud_category="phishing_bancaire",
                    language="fr",
                    severity=9,
                    detection_count=456
                ),
                FraudulentSMSPattern(
                    keywords=["gagné", "prix", "gratuit", "réclamez"],
                    fraud_category="arnaque_gain",
                    language="fr",
                    severity=6,
                    detection_count=123
                ),
                FraudulentSMSPattern(
                    keywords=["covid", "vaccination", "rendez-vous", "cliquez"],
                    fraud_category="phishing_sante",
                    language="fr",
                    severity=7,
                    detection_count=89
                ),
            ]
            session.add_all(sms_patterns)
            await session.commit()
            print(f"✅ {len(sms_patterns)} SMS patterns insérés")
        else:
            print("✅ SMS patterns existent déjà, skip")

        # ═══════════════════════════════════════════════════════════
        # 4. FRAUDULENT DOMAINS
        # ═══════════════════════════════════════════════════════════

        existing = (await session.execute(select(FraudulentDomain))).scalars().first()
        if not existing:
            fraud_domains = [
                FraudulentDomain(
                    domain="fake-bank-secure.com",
                    phishing_type="banking",
                    blocked_count=89,
                    spf_valid=False,
                    dkim_valid=False,
                    reputation_score=0.95
                ),
                FraudulentDomain(
                    domain="paypal-security-update.net",
                    phishing_type="payment",
                    blocked_count=156,
                    spf_valid=False,
                    dkim_valid=False,
                    reputation_score=0.98
                ),
                FraudulentDomain(
                    domain="amazon-delivery-fr.com",
                    phishing_type="delivery",
                    blocked_count=234,
                    spf_valid=False,
                    dkim_valid=False,
                    reputation_score=0.93
                ),
                FraudulentDomain(
                    domain="impots-gouv-remboursement.com",
                    phishing_type="government",
                    blocked_count=312,
                    spf_valid=False,
                    dkim_valid=False,
                    reputation_score=0.97
                ),
            ]
            session.add_all(fraud_domains)
            await session.commit()
            print(f"✅ {len(fraud_domains)} fraudulent domains insérés")
        else:
            print("✅ Fraudulent domains existent déjà, skip")

        print("\n🎉 Seed terminé avec succès!")

if __name__ == "__main__":
    asyncio.run(seed_database())