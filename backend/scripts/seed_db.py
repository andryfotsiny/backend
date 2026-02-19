import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session_maker
from app.models.fraud import FraudulentNumber, FraudulentSMSPattern, FraudulentDomain, FraudType
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select

async def seed_database():
    async with async_session_maker() as session:

        # ═══════════════════════════════════════════════════════════
        # 1. CRÉER COMPTE ORGANISATION PAR DÉFAUT
        # ═══════════════════════════════════════════════════════════

        result = await session.execute(
            select(User).where(User.email == "admin@dyleth.com")
        )
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            email = "admin@dyleth.com"
            phone = "+261340000000"
            password = "Admin@2026"  # Mot de passe temporaire

            email_hash = hashlib.sha256(email.encode()).hexdigest()
            phone_hash = hashlib.sha256(phone.encode()).hexdigest()
            password_hash = get_password_hash(password)

            admin_user = User(
                email=email,
                phone=phone,
                email_hash=email_hash,
                phone_hash=phone_hash,
                password_hash=password_hash,
                role=UserRole.ORGANISATION,
                country_code="MG",
                settings={
                    "theme": "light",
                    "language": "fr",
                    "notifications": True,
                    "auto_block": True
                },
                device_tokens=[],
                report_count=0,
                created_at=datetime.now(timezone.utc),
                last_active=datetime.now(timezone.utc)
            )

            session.add(admin_user)
            await session.commit()  # ← COMMIT ICI pour ne pas perdre le compte si les données plantent
            print("✅ Compte ORGANISATION créé")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            print("   ⚠️  Changez le mot de passe après la première connexion !")
        else:
            print("✅ Compte ORGANISATION existe déjà")

        # ═══════════════════════════════════════════════════════════
        # 2. DONNÉES DE FRAUDE (NUMÉROS, SMS, DOMAINES)
        # ═══════════════════════════════════════════════════════════

        # Vérifier si les données existent déjà
        existing_numbers = await session.execute(select(FraudulentNumber))
        if existing_numbers.scalars().first():
            print("✅ Données de fraude existent déjà, skip insertion")
            return

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

        session.add_all(fraud_numbers)
        session.add_all(sms_patterns)
        session.add_all(fraud_domains)

        await session.commit()

        print("\n✅ Données de fraude insérées avec succès!")
        print(f"   - {len(fraud_numbers)} fraudulent numbers")
        print(f"   - {len(sms_patterns)} SMS patterns")
        print(f"   - {len(fraud_domains)} fraudulent domains")

if __name__ == "__main__":
    asyncio.run(seed_database())