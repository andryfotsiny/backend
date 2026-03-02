import google.generativeai as genai
from app.core.config import settings
import logging
from typing import Optional

class LLMService:
    def __init__(self):
        self.model = None
        self.initialized = False
        
    def _initialize(self):
        if not settings.GEMINI_API_KEY:
            logging.warning("GEMINI_API_KEY not set. LLM features will be disabled.")
            return False
            
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.LLM_MODEL)
            self.initialized = True
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Gemini: {e}")
            return False

    async def generate_answer(self, prompt: str, context: str) -> str:
        if not self.initialized:
            if not self._initialize():
                return "Désolé, le service d'IA de conversation n'est pas configuré actuellement."
        
        full_prompt = f"""
Tu es un expert en cybersécurité pour DYLETH, spécialisé dans la détection de fraudes (SMS, Appels, Emails).
Utilise les informations de contexte suivantes pour répondre à la question de l'utilisateur.
Si tu ne connais pas la réponse avec certitude, dis-le simplement au lieu d'inventer.

CONTEXTE DES FRAUDES RÉCENTES :
{context}

QUESTION DE L'UTILISATEUR :
{prompt}

RÉPONSE (sois précis, préventif et professionnel) :
"""
        try:
            response = await self.model.generate_content_async(full_prompt)
            return response.text
        except Exception as e:
            logging.error(f"Error generating LLM content: {e}")
            return "Une erreur est survenue lors de la génération de la réponse."

llm_service = LLMService()
