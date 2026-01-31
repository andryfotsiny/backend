import joblib
import numpy as np
from typing import Tuple, Optional
import os
from app.core.config import settings

class MLService:
    def __init__(self):
        self.phone_model = None
        self.sms_model = None
        self.email_model = None
        self.vectorizer = None
        
    def load_models(self):
        model_path = settings.ML_MODEL_PATH
        try:
            if os.path.exists(f"{model_path}/phone_model.pkl"):
                self.phone_model = joblib.load(f"{model_path}/phone_model.pkl")
            if os.path.exists(f"{model_path}/sms_model.pkl"):
                self.sms_model = joblib.load(f"{model_path}/sms_model.pkl")
            if os.path.exists(f"{model_path}/vectorizer.pkl"):
                self.vectorizer = joblib.load(f"{model_path}/vectorizer.pkl")
        except:
            pass
    
    def predict_phone(self, phone: str, features: dict) -> Tuple[bool, float]:
        if not self.phone_model:
            return False, 0.0
        
        try:
            feature_vector = self._extract_phone_features(phone, features)
            proba = self.phone_model.predict_proba([feature_vector])[0]
            is_fraud = proba[1] > settings.FRAUD_CONFIDENCE_THRESHOLD
            confidence = float(proba[1])
            return is_fraud, confidence
        except:
            return False, 0.0
    
    def predict_sms(self, content: str, sender: str) -> Tuple[bool, float, list]:
        if not self.sms_model or not self.vectorizer:
            return self._rule_based_sms(content)
        
        try:
            text_features = self.vectorizer.transform([content])
            proba = self.sms_model.predict_proba(text_features)[0]
            is_fraud = proba[1] > settings.FRAUD_CONFIDENCE_THRESHOLD
            confidence = float(proba[1])
            risk_factors = self._extract_risk_factors(content)
            return is_fraud, confidence, risk_factors
        except:
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
            features.get("call_count", 0)
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
