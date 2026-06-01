# app/core/telemarketing.py
from app.core.phone_utils import normalize_phone_number

# Plages officielles ARCEP réservées au démarchage commercial (prospection téléphonique)
# Source : Plan de numérotation ARCEP — décision n° 2021-1492 et suivantes
# Dernière mise à jour : 2025
FR_TELEMARKETING_PREFIXES = [
    # Tranche 01xx — Île-de-France
    "0162", "0163", "0164", "0165", "0166", "0167", "0168", "0169",
    # Tranche 02xx — Nord-Ouest
    "02688", "02689",
    # Tranche 027x — National
    "0270", "0271", "0272", "0273",
    # Tranche 037x — Est
    "0377", "0378", "0379",
    # Tranche 042x — Sud-Est
    "0424", "0425", "0426", "0427",
    # Tranche 056x — Sud-Ouest
    "0568", "0569",
    # Tranche 0598x — Outre-mer
    "05987", "05988", "05989",
    # Tranche 094xx — National (grandes plateformes)
    "09475", "09476", "09477", "09478", "09479",
    "0948", "0949",
    # Tranche 033x — Centre
    "0337", "0338",
    # Numéros courts connus pour démarchage agressif (non ARCEP mais reportés)
    "0899",  # Surtaxés
]


def _normalize_fr(phone: str) -> str:
    return (
        phone
        .replace(" ", "")
        .replace(".", "")
        .replace("-", "")
        .replace("+33", "0")
        .replace("0033", "0")
    )


def is_telemarketing_number(phone: str, country: str = "FR") -> bool:
    if country != "FR":
        return False
    normalized = _normalize_fr(phone)
    return any(normalized.startswith(prefix) for prefix in FR_TELEMARKETING_PREFIXES)


TELEMARKETING_RESPONSE = {
    "is_fraud": True,
    "confidence": 0.6,
    "category": "telemarketing",
    "reason": "Numéro appartenant aux plages officielles de télémarketing ARCEP (France)",
    "action": "warn",
    "similar_cases": 0,
    "status": "telemarketing",
    "business": None,
}