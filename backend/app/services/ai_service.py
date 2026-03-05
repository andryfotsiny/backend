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
        if phones and (wants_analysis or len(phones[0]) > 9):
            phone = phones[0]
            result = await detection_service.check_phone(db, phone, "FR", user_id)

            if result["is_fraud"]:
                response = (
                    f"Attention ! J'ai analysé le numéro {phone} et il est répertorié comme **FRAUDULEUX** "
                    f"({result.get('category', 'scam')}). Motifs : {result.get('reason', 'Signalé par la communauté')}. "
                    f"Confiance : {result['confidence']:.0%}."
                )
            else:
                response = (
                    f"Le numéro {phone} ne figure pas dans nos bases de fraude actuelles "
                    f"et son comportement semble normal (Indice de confiance : {result['confidence']:.0%})."
                )
            return {"response": response, "context": []}

        # 4. Logique pour les messages (SMS, Email, Chat)
        # On déclenche l'analyse sur le content NETTOYÉ
        suspect_keywords = [
            "urgent",
            "payez",
            "cliquez",
            "compte",
            "bloqué",
            "lien",
            "remboursement",
            "amende",
            "livraison",
            "frais",
            "colis",
            "chronopost",
            "la poste",
        ]
        is_suspect = any(kw in cleaned_content.lower() for kw in suspect_keywords)

        if wants_analysis or has_url or is_suspect:
            # Utiliser cleaned_content pour éviter de polluer le modèle ML avec "scan ce message"
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
            elif wants_analysis or has_url:
                # Si l'utilisateur a explicitement demandé ou s'il y a une URL, on confirme que c'est safe
                response = (
                    "Analyse terminée : Je n'ai détecté aucun signe de fraude connu dans ce message. "
                    "Le contenu semble légitime selon nos modèles."
                )
                return {"response": response, "context": []}

        # 5. Fallback - Questions générales
        if any(
            kw in message_lower for kw in ["comment", "fonctionne", "detect", "méthode"]
        ):
            response = (
                "Je suis l'assistant DYLETH. J'utilise du Machine Learning (Random Forest) "
                "et des bases de données de fraude pour vous protéger. "
                "Donnez-moi un numéro ou un texte de message à analyser !"
            )
        else:
            response = (
                "Bonjour ! Je suis l'IA de DYLETH. Je peux analyser un numéro de téléphone ou un message pour vous. "
                "Posez-moi une question ou donnez-moi un élément à vérifier (ex: 'scan ce message : ...')."
            )

        return {"response": response, "context": []}


ai_service = AIService()
