from typing import Tuple


class MLService:
    def __init__(self):
        self.phone_model = None
        self.sms_model = None
        self.email_model = None
        self.vectorizer = None

    def load_models(self):
        pass

    def predict_phone(self, phone: str, features: dict) -> Tuple[bool, float]:
        """Simple rule-based phone prediction placeholder."""
        if not phone:
            return False, 0.0

        score = 0.0
        # Suspicious length (too short or too long for standard numbers)
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        if len(clean_phone) < 8 or len(clean_phone) > 15:
            score += 0.4

        # Call count features (simulating frequency detection)
        call_count = features.get("call_count", 0)
        if call_count > 50:  # High frequency calling
            score += 0.5
        elif call_count > 10:
            score += 0.2

        # Suspicious hour (late night/early morning for spam bots)
        hour = features.get("hour", 0)
        if hour < 7 or hour > 21:
            score += 0.1

        is_fraud = score >= 0.5
        confidence = min(score, 0.95)
        return is_fraud, confidence

    def predict_sms(self, content: str, sender: str) -> Tuple[bool, float, list]:
        return self._rule_based_sms(content)

    def predict_email(self, sender: str, subject: str, body: str) -> Tuple[bool, float]:
        combined = f"{subject} {body}"
        is_fraud, confidence, _ = self.predict_sms(combined, sender)
        return is_fraud, confidence

    def _extract_phone_features(self, phone: str, features: dict) -> list:
        return [
            len(phone),
            int(phone.startswith("+")),
            features.get("hour", 0),
            features.get("call_count", 0),
        ]

    def _rule_based_sms(self, content: str) -> Tuple[bool, float, list]:
        content_lower = content.lower()
        risk_factors = []
        score = 0

        urgent_keywords = ["urgent", "immédiat", "maintenant", "rapidement", "vite"]
        money_keywords = ["payez", "paiement", "frais", "€", "argent", "remboursement"]
        link_keywords = ["http://", "https://", "bit.ly", "cliquez", "lien"]
        threat_keywords = ["bloqué", "suspendu", "limite", "expire", "problème"]

        for keyword in urgent_keywords:
            if keyword in content_lower:
                risk_factors.append("Urgence factice")
                score += 0.2
                break

        for keyword in money_keywords:
            if keyword in content_lower:
                risk_factors.append("Demande de paiement")
                score += 0.3
                break

        for keyword in link_keywords:
            if keyword in content_lower:
                risk_factors.append("Lien suspect")
                score += 0.25
                break

        for keyword in threat_keywords:
            if keyword in content_lower:
                risk_factors.append("Message de menace")
                score += 0.15
                break

        is_fraud = score >= 0.5
        confidence = min(score, 0.95)

        return is_fraud, confidence, risk_factors


ml_service = MLService()
