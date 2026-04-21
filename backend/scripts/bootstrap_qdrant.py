"""
Script de bootstrap Qdrant avec exemples de phishing connus.

Remplit Qdrant avec ~50 exemples de SMS/emails frauduleux hardcodés,
pour que le RAG ait une base de comparaison dès le premier jour.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.bootstrap_qdrant
"""

import logging
from datetime import datetime
from app.services.rag_service import rag_service
from app.rag.embeddings import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# SMS de phishing connus (FR/MG)
# ============================================================
SMS_PHISHING_EXAMPLES = [
    # --- Faux colis / livraison ---
    {
        "content": "URGENT! Votre colis DHL est retenu. Payez 2€ maintenant: http://bit.ly/abc123",
        "category": "phishing_livraison",
    },
    {
        "content": "Votre colis Chronopost est bloqué en douane. Réglez 1.99€ ici: https://t.co/xyz",
        "category": "phishing_livraison",
    },
    {
        "content": "Colissimo: votre paquet attend. Frais de livraison 2.50€: bit.ly/colissimo-pay",
        "category": "phishing_livraison",
    },
    {
        "content": "La Poste: échec de livraison. Reprogrammez ici: https://laposte-fr.net/delivery",
        "category": "phishing_livraison",
    },
    {
        "content": "UPS: votre colis nécessite un paiement de 3€ pour livraison: http://ups-fr.click",
        "category": "phishing_livraison",
    },
    {
        "content": "Amazon: votre commande est en attente de paiement. Cliquez: http://amaz0n-fr.shop/verify",
        "category": "phishing_livraison",
    },
    {
        "content": "FedEx: Adresse incorrecte. Mettez à jour: https://fedex-update.info/correct",
        "category": "phishing_livraison",
    },

    # --- Phishing bancaire ---
    {
        "content": "Votre compte bancaire sera bloqué dans 24h. Confirmez ici: http://secu-banque.fr/login",
        "category": "phishing_bancaire",
    },
    {
        "content": "ALERTE BNP: connexion suspecte détectée. Vérifiez votre compte: bnp-securise.com/verif",
        "category": "phishing_bancaire",
    },
    {
        "content": "Crédit Agricole: nouvelle opération à valider. Authentifiez-vous: ca-secure.click",
        "category": "phishing_bancaire",
    },
    {
        "content": "Société Générale: votre carte a été bloquée. Débloquez ici: http://sg-debloq.net",
        "category": "phishing_bancaire",
    },
    {
        "content": "LCL: virement de 2450€ en attente. Confirmez: https://lcl-valid.fr/op",
        "category": "phishing_bancaire",
    },
    {
        "content": "Votre CB est désactivée. Réactivez immédiatement: bit.ly/cb-reactiv",
        "category": "phishing_bancaire",
    },
    {
        "content": "Boursorama: transaction suspecte de 890€. Bloquez maintenant: boursorama-fr.net",
        "category": "phishing_bancaire",
    },

    # --- Services publics / impôts ---
    {
        "content": "Impôts: remboursement de 378€ disponible. Réclamez: https://impots-gouv-remb.fr",
        "category": "phishing_administration",
    },
    {
        "content": "CAF: votre dossier incomplet. Mettez à jour sous 48h: caf-update.fr/dossier",
        "category": "phishing_administration",
    },
    {
        "content": "Ameli: remboursement santé en attente 156€. Réclamez: ameli-rembours.com/claim",
        "category": "phishing_administration",
    },
    {
        "content": "Pôle Emploi: nouveau paiement. Actualisez vos infos: https://pole-empl0i.fr",
        "category": "phishing_administration",
    },
    {
        "content": "URSSAF: régularisation requise. Payez 234€: urssaf-pay.net/regular",
        "category": "phishing_administration",
    },
    {
        "content": "ANTS: votre carte grise prête. Frais de port 1.50€: ants-gouv.click/cg",
        "category": "phishing_administration",
    },

    # --- Arnaque au gain ---
    {
        "content": "FÉLICITATIONS! Vous avez gagné 10000€. Réclamez votre prix: http://gain-express.fr",
        "category": "arnaque_gain",
    },
    {
        "content": "Tirage spécial Loto! Vous avez été sélectionné. Prix: 5000€. Cliquez: loto-win.net",
        "category": "arnaque_gain",
    },
    {
        "content": "Cadeau Samsung offert! Derniers 5 iPhone 15 disponibles: samsung-cadeau.fr",
        "category": "arnaque_gain",
    },
    {
        "content": "Vous avez gagné un voyage aux Maldives! Validez ici: voyage-gagne.com/valid",
        "category": "arnaque_gain",
    },

    # --- Crypto / investissement ---
    {
        "content": "Binance: connexion depuis Russie détectée. Sécurisez: https://binance-secu.io",
        "category": "phishing_crypto",
    },
    {
        "content": "Votre portefeuille Coinbase a été gelé. Débloquez: coinbase-unlock.net",
        "category": "phishing_crypto",
    },
    {
        "content": "Opportunité Bitcoin! Doublez vos investissements en 7j: crypto-profit.click",
        "category": "scam_investissement",
    },
    {
        "content": "Trading garanti 500€/jour. Inscrivez-vous: trading-easy.fr/join",
        "category": "scam_investissement",
    },

    # --- Fausses livraisons / services ---
    {
        "content": "Netflix: paiement échoué. Mettez à jour votre carte: netflix-billing.co",
        "category": "phishing_service",
    },
    {
        "content": "Spotify Premium expire dans 24h. Renouvelez: spotify-renew.fr",
        "category": "phishing_service",
    },
    {
        "content": "Votre abonnement Apple a été prolongé 79.99€. Annulez: apple-cancel.net",
        "category": "phishing_service",
    },
    {
        "content": "Microsoft: compte suspendu. Réactivez ici: microsoft-fr.click/reactive",
        "category": "phishing_service",
    },

    # --- Sextorsion / menaces ---
    {
        "content": "Nous avons piraté votre téléphone. Payez 500€ en Bitcoin sous 48h: BTC wallet...",
        "category": "sextorsion",
    },
    {
        "content": "Vos données sont en ligne. Protégez-vous maintenant: http://protect-fr.net",
        "category": "menace",
    },

    # --- MG / Afrique francophone ---
    {
        "content": "Telma: votre ligne sera désactivée. Rechargez maintenant: telma-recharge.mg",
        "category": "phishing_telecom",
    },
    {
        "content": "Orange Money: transfert de 500000 Ar en attente. Validez: orange-mg.click",
        "category": "phishing_telecom",
    },
    {
        "content": "Airtel Money: votre solde a été crédité. Retirez: airtel-withdraw.mg",
        "category": "phishing_telecom",
    },

    # --- COVID / santé ---
    {
        "content": "Votre pass sanitaire expire. Renouvelez en ligne: pass-sanit.fr/renew",
        "category": "phishing_sante",
    },
    {
        "content": "Rappel vaccin COVID obligatoire. Prenez RDV: vaccin-covid.click",
        "category": "phishing_sante",
    },
]


# ============================================================
# Emails de phishing connus
# ============================================================
EMAIL_PHISHING_EXAMPLES = [
    {
        "content": "URGENT action requise Votre compte bancaire sera bloqué dans 24h. Confirmez immédiatement vos identifiants pour éviter la suspension de votre compte.",
        "category": "phishing_bancaire",
    },
    {
        "content": "Remboursement impôts 450 euros Cher contribuable, vous êtes éligible à un remboursement de 450€. Cliquez ici pour réclamer votre argent avant expiration.",
        "category": "phishing_administration",
    },
    {
        "content": "Votre colis est en attente Nous avons tenté de livrer votre colis. Payez les frais de 2.99€ pour reprogrammer la livraison.",
        "category": "phishing_livraison",
    },
    {
        "content": "Alerte sécurité PayPal Activité suspecte détectée sur votre compte. Vérifiez votre identité immédiatement en cliquant sur ce lien.",
        "category": "phishing_paiement",
    },
    {
        "content": "Félicitations gagnant loterie Vous avez gagné 1 million d'euros à la loterie internationale. Envoyez vos coordonnées bancaires pour recevoir vos gains.",
        "category": "arnaque_gain",
    },
    {
        "content": "Mise à jour mot de passe Microsoft Votre mot de passe expire aujourd'hui. Cliquez ici pour le renouveler avant la suspension du compte.",
        "category": "phishing_service",
    },
    {
        "content": "Facture Netflix impayée Nous n'avons pas pu débiter votre carte. Mettez à jour vos informations de paiement sous 24h.",
        "category": "phishing_service",
    },
    {
        "content": "Votre héritage de 2 millions Je suis avocat, un lointain parent vous a laissé 2M€. Envoyez vos documents d'identité pour procéder.",
        "category": "arnaque_avocat",
    },
    {
        "content": "Confirmer livraison Amazon Votre commande Amazon attend confirmation. Validez votre adresse et paiement ici.",
        "category": "phishing_livraison",
    },
    {
        "content": "Binance alerte connexion Connexion depuis un nouvel appareil détectée. Sécurisez votre compte en validant vos identifiants.",
        "category": "phishing_crypto",
    },
]


def bootstrap_qdrant():
    """Remplit Qdrant avec les exemples hardcodés."""

    logger.info("Initializing RAG service...")
    rag_service.connect()
    if not rag_service.enabled:
        logger.error("❌ Qdrant unavailable.")
        return

    logger.info("Loading embedding model (peut prendre ~30s au premier run)...")
    embedding_service.load_model()
    if not embedding_service.enabled:
        logger.error("❌ Embedding model unavailable.")
        return

    # --- SMS ---
    logger.info(f"Indexing {len(SMS_PHISHING_EXAMPLES)} SMS phishing examples...")
    sms_added = 0
    for example in SMS_PHISHING_EXAMPLES:
        try:
            vector = embedding_service.get_embedding(example["content"])
            if vector:
                rag_service.add_vector(
                    vector=vector,
                    payload={
                        "content": example["content"],
                        "type": "sms_scam",
                        "fraud_category": example["category"],
                        "verified": True,
                        "source": "bootstrap",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                sms_added += 1
        except Exception as e:
            logger.warning(f"Failed to index SMS: {e}")

    # --- Emails ---
    logger.info(f"Indexing {len(EMAIL_PHISHING_EXAMPLES)} email phishing examples...")
    email_added = 0
    for example in EMAIL_PHISHING_EXAMPLES:
        try:
            vector = embedding_service.get_embedding(example["content"])
            if vector:
                rag_service.add_vector(
                    vector=vector,
                    payload={
                        "content": example["content"],
                        "type": "email_scam",
                        "fraud_category": example["category"],
                        "verified": True,
                        "source": "bootstrap",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                email_added += 1
        except Exception as e:
            logger.warning(f"Failed to index email: {e}")

    logger.info("=" * 60)
    logger.info("✅ BOOTSTRAP TERMINÉ")
    logger.info(f"   SMS indexed:    {sms_added} / {len(SMS_PHISHING_EXAMPLES)}")
    logger.info(f"   Emails indexed: {email_added} / {len(EMAIL_PHISHING_EXAMPLES)}")
    logger.info(f"   Total vectors:  {sms_added + email_added}")
    logger.info("=" * 60)
    logger.info("Le RAG peut maintenant détecter les fraudes similaires !")


if __name__ == "__main__":
    bootstrap_qdrant()