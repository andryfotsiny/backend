import joblib
from pathlib import Path
from typing import Tuple, List
import logging


class MLService:
    def __init__(self):
        self.phone_model = None
        self.sms_model = None
        self.email_model = None
        self.vectorizer = None

        # Paths
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.model_dir = self.base_dir / "models" / "ml_models"

    def load_models(self):
        """Charger les modèles entraînés depuis le disque"""
        try:
            sms_model_path = self.model_dir / "sms_model.pkl"
            vectorizer_path = self.model_dir / "vectorizer.pkl"

            logging.info(
                "Attempting to load ML models from: %s", self.model_dir.absolute()
            )
            if sms_model_path.exists() and vectorizer_path.exists():
                self.sms_model = joblib.load(sms_model_path)
                self.vectorizer = joblib.load(vectorizer_path)
                logging.info("ML models loaded successfully from %s", sms_model_path)
            else:
                logging.warning("ML models not found at %s", self.model_dir)
        except Exception as e:
            logging.error("Failed to load ML models: %s", e)

    def predict_phone(self, phone: str, features: dict) -> Tuple[bool, float]:
        """Simple rule-based phone prediction placeholder."""
        if not phone:
            return False, 0.0

        score = 0.0
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        if len(clean_phone) < 8 or len(clean_phone) > 15:
            score += 0.4

        call_count = features.get("call_count", 0)
        if call_count > 50:
            score += 0.5
        elif call_count > 10:
            score += 0.2

        hour = features.get("hour", 0)
        if hour < 7 or hour > 21:
            score += 0.1

        is_fraud = score >= 0.5
        confidence = min(score, 0.95)
        return is_fraud, confidence

    def predict_sms(self, content: str, sender: str) -> Tuple[bool, float, List[str]]:
        """Prédit si un SMS est une fraude en utilisant le modèle ML si dispo, sinon règles."""
        risk_factors = []

        if self.sms_model and self.vectorizer:
            try:
                features = self.vectorizer.transform([content])
                prediction = self.sms_model.predict(features)[0]
                probabilities = self.sms_model.predict_proba(features)[0]

                is_fraud = bool(prediction == 1)
                confidence = float(probabilities[prediction])

                if is_fraud:
                    risk_factors.append("Détection ML (RandomForest)")
                    # Ajouter aussi quelques règles pour les risk_factors
                    _, _, rule_risks = self._rule_based_sms(content)
                    risk_factors.extend(rule_risks)

                return is_fraud, confidence, list(set(risk_factors))
            except Exception as e:
                logging.error("ML prediction failed, falling back to rules: %s", e)

        return self._rule_based_sms(content)

    def predict_email(self, sender: str, subject: str, body: str) -> Tuple[bool, float]:
        """Prédit si un email est du phishing."""
        combined = f"{subject} {body}"
        # On utilise le même classifieur de texte que pour les SMS pour le moment
        is_fraud, confidence, _ = self.predict_sms(combined, sender)
        return is_fraud, confidence

    def _extract_phone_features(self, phone: str, features: dict) -> List:
        return [
            len(phone),
            int(phone.startswith("+")),
            features.get("hour", 0),
            features.get("call_count", 0),
        ]

    def _rule_based_sms(self, content: str) -> Tuple[bool, float, List[str]]:
        content_lower = content.lower()
        risk_factors = []
        score = 0

        urgent_keywords = [
            "urgent",
            "immédiat",
            "maintenant",
            "rapidement",
            "vite",
            "sous 24h",
            "sous 48h",
        ]
        money_keywords = [
            "payez",
            "paiement",
            "frais",
            "€",
            "argent",
            "remboursement",
            "amende",
            "taxe",
        ]
        link_keywords = [
            "http://",
            "https://",
            "bit.ly",
            "cliquez",
            "lien",
            "connectez",
            "visitez",
        ]
        threat_keywords = [
            "bloqué",
            "suspendu",
            "limite",
            "expire",
            "problème",
            "sécurité",
            "suspect",
        ]
        delivery_brands = ["chronopost", "dhl", "ups", "fedex", "colissimo"]

        # Détection d'intentions de livraison légitime (ex: locaux)
        legit_indicators = [
            "ici en bas",
            "gardien",
            "voisin",
            "boite aux lettres",
            "bal",
        ]
        is_potentially_legit = any(kw in content_lower for kw in legit_indicators)

        for keyword in urgent_keywords:
            if keyword in content_lower:
                risk_factors.append("Urgence factice")
                score += 0.2
                break

        for keyword in money_keywords:
            if keyword in content_lower:
                risk_factors.append("Demande de paiement ou remboursement")
                score += 0.3
                break

        for keyword in link_keywords:
            if keyword in content_lower:
                risk_factors.append("Lien suspect")
                score += 0.3
                break

        for keyword in threat_keywords:
            if keyword in content_lower:
                risk_factors.append("Message de menace ou alerte")
                score += 0.2
                break

        # Les marques de livraison seules sont peu risquées
        for keyword in delivery_brands:
            if keyword in content_lower:
                risk_factors.append("Mention service de livraison")
                score += 0.1
                break

        has_delivery = any(
            kw in content_lower for kw in (delivery_brands + ["livraison", "colis"])
        )
        has_link = any(kw in content_lower for kw in link_keywords)
        has_payment = any(kw in content_lower for kw in money_keywords)

        if has_delivery and (has_link or has_payment):
            score += 0.3
            risk_factors.append("Combinaison suspecte (Livraison + Lien/Paiement)")

        if is_potentially_legit:
            score -= 0.3

        is_fraud = score >= 0.5
        confidence = max(0.0, min(score, 0.95))

        return is_fraud, confidence, list(set(risk_factors))


ml_service = MLService()
