# app/core/telemarketing.py
from app.core.phone_utils import normalize_phone_number

FR_TELEMARKETING_PREFIXES = [
    "0162", "0163", "02688", "02689",
    "0270", "0271", "0377", "0378",
    "0424", "0425", "0568", "0569",
    "05987", "05988", "05989",
    "09475", "09476", "09477", "09478", "09479",
    "0948", "0949",
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