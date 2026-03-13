import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.detection.service import detection_service


class AIService:
    async def get_response(
        self, db: AsyncSession, message: str, user_id: Optional[str] = None
    ) -> dict:
        """Génère une réponse intelligente basée sur le contexte du message."""

        message_lower = message.lower()

        # 1. Détection d'intentions (Commandes)
        analysis_keywords = [
            "scan",
            "analyser",
            "vérifie",
            "vérifier",
            "check",
            "test",
            "contrôle",
            "analyse",
        ]
        wants_analysis = any(kw in message_lower for kw in analysis_keywords)

        # Nettoyage du message pour l'analyse (on enlève les commandes au début)
        # Supprime "scan ce message : ", "analyse : ", etc.
        cleaned_content = message
        prefixes_to_strip = [
            r"^(scan|analyser|vérifie|vérifier|check|test|contrôle|analyse)\s+(ce|le)?\s*(message|sms|email|numéro)?\s*[:\-\s]+",
            r"^[:\-\s]+",
        ]
        for pattern in prefixes_to_strip:
            cleaned_content = re.sub(
                pattern, "", cleaned_content, flags=re.IGNORECASE
            ).strip()

        # 2. Détection d'entités (Téléphone, URL) sur le message COMPLET
        phone_pattern = r"(\+?\d{8,15})"
        phones = re.findall(phone_pattern, message)

        url_pattern = r"(https?://\S+|www\.\S+|bit\.ly/\S+)"
        has_url = re.search(url_pattern, message) is not None

        # 3. Logique pour les numéros de téléphone
        if phones:
            phone = phones[0]
            result = await detection_service.check_phone(db, phone, "FR", user_id)

            if result["is_fraud"]:
                response = (
                    f"Attention ! J'ai analysé le numéro {phone} et il est répertorié comme **FRAUDULEUX** "
                    f"({result.get('category', 'scam')}). Motifs : {result.get('reason', 'Signalé par la communauté')}. "
                    f"Confiance : {result['confidence']:.0%}."
                )
                return {"response": response, "context": []}
            elif wants_analysis or len(phone) > 9:
                response = (
                    f"Le numéro {phone} ne figure pas dans nos bases de fraude actuelles "
                    f"et son comportement semble normal (Indice de confiance : {result['confidence']:.0%})."
                )
                return {"response": response, "context": []}

        # 4. Analyse systématique du message via le modèle ML
        # S'il y a du texte (plus qu'un simple mot), on le passe toujours au modèle
        if len(cleaned_content) > 3:
            result = await detection_service.check_sms(
                db, cleaned_content, "unknown", user_id
            )

            if result["is_fraud"]:
                response = (
                    f"Analyse terminée : Ce message présente des caractéristiques de **FRAUDE** "
                    f"({result.get('category', 'phishing')}).\n"
                    f" Facteurs de risque : {', '.join(result.get('risk_factors', []))}.\n"
                    "Recommandation : Ne pas interagir avec ce message."
                )
                return {"response": response, "context": []}

            # Si on arrive ici, l'IA n'a pas détecté de fraude.
            # On vérifie si c'est une question générale avant d'affirmer que c'est un message "safe".
            fallback_keywords = ["comment", "fonctionne", "detect", "méthode", "bonjour", "salut"]
            is_general_question = any(kw in message_lower for kw in fallback_keywords)

            if not is_general_question or wants_analysis or has_url:
                response = (
                    "Analyse terminée : Je n'ai détecté aucun signe de fraude connu dans ce message. "
                    "Le contenu semble légitime selon mes modèles."
                )
                return {"response": response, "context": []}

        # 5. Fallback - Questions générales et accueil
        if any(kw in message_lower for kw in ["comment", "fonctionne", "detect", "méthode"]):
            response = (
                "Je suis l'assistant DYLETH. J'utilise du Machine Learning (Random Forest) "
                "et des bases de données de fraude pour vous protéger. "
                "Copiez-collez simplement un numéro ou un message pour que je l'analyse !"
            )
        else:
            response = (
                "Bonjour ! Je suis l'IA de DYLETH. Je peux analyser un numéro de téléphone ou un message pour vous. "
                "Copiez-collez simplement le texte ou le numéro ici."
            )

        return {"response": response, "context": []}


ai_service = AIService()
