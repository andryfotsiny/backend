import re
import httpx
import logging
import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.detection.service import detection_service
from app.core.config import settings


class AIService:
    async def _ask_ollama(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Appelle l'API Ollama pour générer une réponse."""
        try:
            # On combine le system prompt et le prompt pour plus de compatibilité
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(settings.OLLAMA_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "Désolé, je ne peux pas générer de réponse pour le moment.")
        except Exception:
            logging.exception("Ollama error")
            return "Désolé, une erreur est survenue lors de la génération par l'IA. Vérifiez que Ollama est bien lancé."

    async def get_response(
        self, db: AsyncSession, message: str, user_id: Optional[str] = None
    ) -> dict:
        """Génère une réponse intelligente basée sur le contexte du message."""
        start_time = time.time()

        message_lower = message.lower()
    
        analysis_keywords = [
            "scan", "analyser", "vérifie", "vérifier", "check", "test", "contrôle", "analyse"
        ]
        wants_analysis = any(kw in message_lower for kw in analysis_keywords)

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
                return {
                    "response": response, 
                    "context": [],
                    "response_time_s": round(time.time() - start_time, 2)
                }
            elif wants_analysis or len(phone) > 9:
                response = (
                    f"Le numéro {phone} ne figure pas dans nos bases de fraude actuelles "
                    f"et son comportement semble normal (Indice de confiance : {result['confidence']:.0%})."
                )
                return {
                    "response": response, 
                    "context": [],
                    "response_time_s": round(time.time() - start_time, 2)
                }

        # 4. Analyse systématique du message via le modèle ML
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
                return {
                    "response": response, 
                    "context": [],
                    "response_time_s": round(time.time() - start_time, 2)
                }

            # Fallback
            fallback_keywords = ["comment", "fonctionne", "detect", "méthode", "bonjour", "salut"]
            is_general_question = any(kw in message_lower for kw in fallback_keywords)

            if not is_general_question or wants_analysis or has_url:
                response = (
                    "Analyse terminée : Je n'ai détecté aucun signe de fraude connu dans ce message. "
                    "Le contenu semble légitime selon mes modèles."
                )
                return {
                    "response": response, 
                    "context": [],
                    "response_time_s": round(time.time() - start_time, 2)
                }

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

        return {
            "response": response, 
            "context": [],
            "response_time_s": round(time.time() - start_time, 2)
        }

    async def get_ollama_response(
        self, db: AsyncSession, message: str, user_id: Optional[str] = None
    ) -> dict:
        """Génère une réponse via Ollama en intégrant le contexte DYLETH."""
        start_time = time.time()
        
        # Nettoyage
        cleaned_content = message
        prefixes_to_strip = [
            r"^(scan|analyser|vérifie|vérifier|check|test|contrôle|analyse)\s+(ce|le)?\s*(message|sms|email|numéro)?\s*[:\-\s]+",
            r"^[:\-\s]+",
        ]
        for pattern in prefixes_to_strip:
            cleaned_content = re.sub(pattern, "", cleaned_content, flags=re.IGNORECASE).strip()

        phone_pattern = r"(\+?\d{8,15})"
        phones = re.findall(phone_pattern, message)

        # Contexte technique
        detection_context = ""

        # Vérification téléphone
        if phones:
            phone = phones[0]
            phone_result = await detection_service.check_phone(db, phone, "FR", user_id)
            if phone_result["is_fraud"]:
                detection_context += (
                    f"- Téléphone {phone} : FRAUDULEUX ({phone_result.get('category')}). "
                    f"Motif : {phone_result.get('reason')}. Confiance : {phone_result['confidence']:.0%}.\n"
                )
            else:
                detection_context += f"- Téléphone {phone} : Non répertorié comme fraude.\n"

        # Vérification SMS
        if len(cleaned_content) > 3:
            sms_result = await detection_service.check_sms(db, cleaned_content, "unknown", user_id)
            if sms_result["is_fraud"]:
                risks = ", ".join(sms_result.get("risk_factors", []))
                detection_context += (
                    f"- Message : FRAUDULEUX ({sms_result.get('category', 'phishing')}). "
                    f"Facteurs de risque : {risks}. Confiance : {sms_result['confidence']:.0%}.\n"
                )

        # Ollama
        system_prompt = (
            "Tu es DYLETH, l'assistant IA expert en cybersécurité et détection de fraude. "
            "Ton rôle est d'aider les utilisateurs à identifier les arnaques (SMS, emails, numéros de téléphone). "
            "Réponds de manière concise, professionnelle et rassurante. "
            "Si DYLETH a détecté une fraude dans le contexte fourni, sois ferme et conseille de ne pas interagir."
        )

        prompt = f"L'utilisateur a envoyé : \"{message}\"\n\n"
        if detection_context:
            prompt += f"Résultats d'analyse technique de DYLETH :\n{detection_context}\n"
        prompt += "Génère une réponse adaptée à l'utilisateur."

        llm_response = await self._ask_ollama(prompt, system_prompt)
        return {
            "response": llm_response, 
            "context": [],
            "response_time_s": round(time.time() - start_time, 2)
        }


ai_service = AIService()
