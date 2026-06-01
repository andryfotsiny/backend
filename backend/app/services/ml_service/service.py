import joblib
from pathlib import Path
from typing import Tuple, List
import logging
import re


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
        """
        Détection de fraude par heuristiques enrichies.
        Retourne (is_fraud, confidence) où confidence ∈ [0, 1].
        """
        if not phone:
            return False, 0.0

        score = 0.0
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        # Longueur anormale
        if len(clean_phone) < 8 or len(clean_phone) > 15:
            score += 0.35

        # Heure d'appel suspecte (avant 7h ou après 21h)
        hour = features.get("hour", 12)
        if hour < 7 or hour > 21:
            score += 0.15

        # Fréquence d'appels élevée
        call_count = features.get("call_count", 0)
        if call_count > 50:
            score += 0.50
        elif call_count > 20:
            score += 0.30
        elif call_count > 10:
            score += 0.15

        # Préfixes internationaux fréquemment usurpés
        suspicious_prefixes = [
            "+1900", "+1800", "+44", "+33970", "+33650",
            "+2250", "+2270", "+22890", "+212",
        ]
        if any(phone.startswith(p) for p in suspicious_prefixes):
            score += 0.20

        # Numéro trop court ou composé de chiffres répétés (ex: 0000000000)
        digits = re.sub(r"\D", "", phone)
        if len(set(digits)) <= 2:
            score += 0.40

        # Nombre de reports communautaires (signal fort)
        report_count = features.get("report_count", 0)
        if report_count >= 5:
            score += 0.60
        elif report_count >= 2:
            score += 0.30

        is_fraud = score >= 0.5
        confidence = round(min(score, 0.99), 3)
        return is_fraud, confidence

    def predict_sms(self, content: str, sender: str) -> Tuple[bool, float, List[str]]:
        """Predict if an SMS is fraudulent using the trained RandomForest model.

        This method now relies solely on the ML model. If the model or vectorizer
        is not loaded, it logs an error and raises a RuntimeError.
        """
        if not (self.sms_model and self.vectorizer):
            logging.error("ML models not loaded; cannot predict SMS.")
            raise RuntimeError("ML models not loaded for SMS prediction")
        try:
            features = self.vectorizer.transform([content])
            prediction = self.sms_model.predict(features)[0]
            probabilities = self.sms_model.predict_proba(features)[0]
            is_fraud = bool(prediction == 1)
            confidence = float(probabilities[prediction])
            risk_factors = ["Détection ML (RandomForest)"]
            return is_fraud, confidence, risk_factors
        except Exception as e:
            logging.error("ML prediction failed: %s", e)
            raise

    def predict_email(self, sender: str, subject: str, body: str) -> Tuple[bool, float]:
        """
        Prédit si un email est du phishing.

        Amélioration vs version précédente :
        - On utilise toujours le modèle SMS (faute d'un modèle email dédié)
          MAIS on ajuste le seuil de décision car les emails légitimes
          contiennent souvent des mots clés (cliquez, urgent, offre...) qui
          font monter faussement le score.
        - On pondère le score par des heuristiques anti-faux-positifs.
        """
        if not (self.sms_model and self.vectorizer):
            logging.error("ML models not loaded; cannot predict email.")
            raise RuntimeError("ML models not loaded for email prediction")

        combined = f"{subject} {body}"

        try:
            features = self.vectorizer.transform([combined])
            probabilities = self.sms_model.predict_proba(features)[0]
            # probability that class == 1 (fraud)
            fraud_proba = float(probabilities[1]) if len(probabilities) > 1 else 0.0
        except Exception as e:
            logging.error("Email ML prediction failed: %s", e)
            raise

        # ============================================================
        # Heuristiques de réduction de faux positifs pour emails
        # ============================================================
        # Le modèle est entraîné sur des SMS courts, donc il sur-réagit
        # sur les emails longs. On compense.

        adjusted_score = fraud_proba
        body_lower = body.lower() if body else ""
        subject_lower = subject.lower() if subject else ""

        # 1. Emails longs = plus probablement légitimes (newsletters, etc.)
        if len(body) > 2000:
            adjusted_score *= 0.7
        elif len(body) > 500:
            adjusted_score *= 0.85

        # 2. Présence d'un lien de désinscription = probablement newsletter légitime
        unsubscribe_patterns = [
            "unsubscribe",
            "se désinscrire",
            "désabonnement",
            "désinscription",
            "opt-out",
            "stop receiving",
        ]
        if any(p in body_lower for p in unsubscribe_patterns):
            adjusted_score *= 0.5

        # 3. Présence de signatures d'entreprise légitimes
        legit_patterns = [
            "sent from",
            "envoyé depuis",
            "this is an automated",
            "message automatique",
            "ne pas répondre",
            "do not reply",
        ]
        if any(p in body_lower for p in legit_patterns):
            adjusted_score *= 0.7

        # 4. BOOST si URL raccourcie suspecte (vrais signaux de phishing)
        shortener_patterns = [
            r"bit\.ly",
            r"tinyurl",
            r"t\.co",
            r"ow\.ly",
            r"goo\.gl",
            r"is\.gd",
        ]
        if any(re.search(p, body_lower) for p in shortener_patterns):
            adjusted_score = min(adjusted_score * 1.3, 1.0)

        # 5. BOOST si demande d'identifiants + urgence combinés
        urgency_words = ["urgent", "immédiat", "immediately", "rapidement", "24h", "48h"]
        credential_words = [
            "mot de passe",
            "password",
            "identifiants",
            "credentials",
            "code pin",
            "carte bancaire",
            "numéro de carte",
        ]
        has_urgency = any(w in body_lower or w in subject_lower for w in urgency_words)
        has_credential_request = any(w in body_lower for w in credential_words)
        if has_urgency and has_credential_request:
            adjusted_score = min(adjusted_score * 1.4, 1.0)

        # Seuil de décision plus strict pour emails (0.65 au lieu de 0.5)
        # afin de réduire les faux positifs.
        EMAIL_FRAUD_THRESHOLD = 0.65
        is_fraud = adjusted_score >= EMAIL_FRAUD_THRESHOLD

        return is_fraud, adjusted_score

    def _extract_phone_features(self, phone: str, features: dict) -> List:
        return [
            len(phone),
            int(phone.startswith("+")),
            features.get("hour", 0),
            features.get("call_count", 0),
        ]


ml_service = MLService()