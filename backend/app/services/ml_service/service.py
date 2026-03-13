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
        """Prédit si un email est du phishing."""
        combined = f"{subject} {body}"
        is_fraud, confidence, _ = self.predict_sms(combined, sender)
        return is_fraud, confidence

    def _extract_phone_features(self, phone: str, features: dict) -> List:
        return [
            len(phone),
            int(phone.startswith("+")),
            features.get("hour", 0),
            features.get("call_count", 0),
        ]


ml_service = MLService()
