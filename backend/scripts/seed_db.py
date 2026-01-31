import asyncio
import sys
sys.path.insert(0, '/app')

from app.db.session import async_session_maker
from app.models.fraud import FraudulentNumber, FraudulentSMSPattern, FraudulentDomain, FraudType
from datetime import datetime

async def seed_database():
    async with async_session_maker() as session:
        
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
            )
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
            )
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
            )
        ]
        
        session.add_all(fraud_numbers)
        session.add_all(sms_patterns)
        session.add_all(fraud_domains)
        
        await session.commit()
        
        print("Database seeded successfully!")
        print(f"  - {len(fraud_numbers)} fraudulent numbers")
        print(f"  - {len(sms_patterns)} SMS patterns")
        print(f"  - {len(fraud_domains)} fraudulent domains")

if __name__ == "__main__":
    asyncio.run(seed_database())
