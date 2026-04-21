"""
DYLETH - Whitelist de domaines et expéditeurs de confiance

Ce module contient la liste statique des domaines (email) et senders (SMS)
considérés comme légitimes et qui ne doivent PAS être analysés par le ML.

IMPORTANT :
- Un domaine/sender dans cette liste ne sera jamais bloqué ("block").
- Si le contenu est très suspect malgré tout, on émet un "warn" (pas block).
- Cette liste complète la table `businesses` (pour les PME)
  et couvre les géants mondiaux qui ne seront jamais en base business.
"""

from typing import Set

# ============================================================
# EMAIL — Domaines de confiance (partie après @)
# ============================================================
# Couvre : Google, Microsoft, Apple, Meta, Amazon, banques,
# crypto, services publics, opérateurs télécom, etc.
TRUSTED_EMAIL_DOMAINS: Set[str] = {
    # --- Google ---
    "google.com",
    "gmail.com",
    "googlemail.com",
    "accounts.google.com",
    "noreply.google.com",
    "youtube.com",

    # --- Microsoft ---
    "microsoft.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "office.com",
    "office365.com",
    "microsoftonline.com",
    "skype.com",
    "linkedin.com",
    "github.com",

    # --- Apple ---
    "apple.com",
    "icloud.com",
    "me.com",
    "mac.com",

    # --- Meta / Facebook ---
    "facebook.com",
    "facebookmail.com",
    "meta.com",
    "instagram.com",
    "whatsapp.com",
    "messenger.com",

    # --- Amazon ---
    "amazon.com",
    "amazon.fr",
    "amazon.co.uk",
    "amazon.de",
    "amazonses.com",
    "aws.amazon.com",

    # --- Crypto / Finance ---
    "binance.com",
    "binance.us",
    "coinbase.com",
    "kraken.com",
    "paypal.com",
    "paypal.fr",
    "stripe.com",
    "wise.com",
    "revolut.com",
    "n26.com",

    # --- Banques françaises ---
    "bnpparibas.com",
    "bnpparibas.net",
    "creditmutuel.fr",
    "credit-agricole.fr",
    "societegenerale.fr",
    "lcl.fr",
    "labanquepostale.fr",
    "caisse-epargne.fr",
    "boursorama.com",
    "hellobank.fr",

    # --- Services publics français ---
    "impots.gouv.fr",
    "service-public.fr",
    "ameli.fr",
    "pole-emploi.fr",
    "francetravail.fr",
    "caf.fr",
    "laposte.fr",
    "laposte.net",
    "ants.gouv.fr",
    "urssaf.fr",

    # --- Opérateurs télécom FR ---
    "orange.fr",
    "orange.com",
    "sfr.fr",
    "bouyguestelecom.fr",
    "free.fr",

    # --- Opérateurs MG ---
    "telma.mg",
    "orange.mg",
    "airtel.mg",

    # --- Autres services populaires ---
    "netflix.com",
    "spotify.com",
    "uber.com",
    "airbnb.com",
    "booking.com",
    "ebay.com",
    "ebay.fr",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "zoom.us",
    "slack.com",
    "dropbox.com",
    "adobe.com",
    "openai.com",
    "anthropic.com",
}


# ============================================================
# SMS — Senders alphanumériques de confiance
# ============================================================
# Certains SMS ne viennent pas d'un numéro mais d'un nom court.
# Comparaison faite en UPPERCASE côté code.
TRUSTED_SMS_SENDERS: Set[str] = {
    # Google
    "GOOGLE",
    "GOOGLEPAY",
    "G-PAY",

    # Microsoft
    "MICROSOFT",
    "MSFT",
    "OFFICE365",

    # Crypto
    "BINANCE",
    "COINBASE",
    "KRAKEN",

    # Paiement
    "PAYPAL",
    "STRIPE",
    "REVOLUT",
    "N26",
    "WISE",

    # Banques FR
    "BNP",
    "BNPPARIBAS",
    "CA-BANQUE",
    "SG",
    "LCL",
    "LABANQUEPOSTALE",

    # Services publics
    "IMPOTS",
    "AMELI",
    "POLE-EMPLOI",
    "CAF",
    "LAPOSTE",

    # Opérateurs FR
    "ORANGE",
    "SFR",
    "BOUYGTEL",
    "FREE",
    "FREEMOBILE",

    # Opérateurs MG
    "TELMA",
    "AIRTEL",
    "ORANGEMG",

    # Autres
    "UBER",
    "AIRBNB",
    "BOOKING",
    "AMAZON",
    "NETFLIX",
    "SPOTIFY",
    "FACEBOOK",
    "INSTAGRAM",
    "WHATSAPP",
    "APPLE",
    "LINKEDIN",
}


# ============================================================
# Helpers publics
# ============================================================

def is_trusted_email_domain(sender_or_domain: str) -> bool:
    """
    Retourne True si l'email (ou le domaine) est de confiance.
    Accepte "user@google.com" ou "google.com".
    Gère aussi les sous-domaines (notify-noreply@google.com → google.com).
    """
    if not sender_or_domain:
        return False

    # Extraire le domaine si c'est une adresse complète
    domain = sender_or_domain.split("@")[-1].strip().lower()

    if not domain:
        return False

    # Match exact
    if domain in TRUSTED_EMAIL_DOMAINS:
        return True

    # Match sous-domaine (ex: notifications.google.com → google.com)
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in TRUSTED_EMAIL_DOMAINS:
            return True

    return False


def is_trusted_sms_sender(sender: str) -> bool:
    """
    Retourne True si le sender SMS alphanumérique est de confiance.
    Normalise : uppercase + suppression espaces/tirets.
    Ignore les numéros de téléphone (commencent par + ou chiffres).
    """
    if not sender:
        return False

    # Si c'est un numéro de téléphone, on sort (géré ailleurs)
    stripped = sender.strip()
    if stripped.startswith("+") or stripped.replace(" ", "").isdigit():
        return False

    normalized = stripped.upper().replace(" ", "").replace("-", "").replace("_", "")
    return normalized in TRUSTED_SMS_SENDERS