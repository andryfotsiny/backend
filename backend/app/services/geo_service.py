import logging
import phonenumbers
import pgeocode
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Cache pour éviter de recréer l'objet pgeocode à chaque ligne
_nominatim_cache: dict = {}

# Pays supportés par pgeocode pour la détection par CP
SUPPORTED_COUNTRIES = ["FR", "DE", "ES", "IT", "BE", "CH", "GB", "PT", "NL", "MA"]


def _get_nominatim(country: str) -> Optional[pgeocode.Nominatim]:
    """Retourne une instance pgeocode cachée pour éviter les recréations."""
    if country not in _nominatim_cache:
        try:
            _nominatim_cache[country] = pgeocode.Nominatim(country)
        except Exception:
            _nominatim_cache[country] = None
    return _nominatim_cache[country]


def _detect_from_tel(tel: str, country_hint: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Étape 1 : Détecte le pays et le préfixe depuis le numéro de téléphone.
    Retourne (code_pays, prefixe) ou None si échec.

    Exemple :
        "465856371", "FR" → parse avec hint "FR" → pays: "FR", préfixe: "+33"
        "+12025551234" → parse direct → pays: "US", préfixe: "+1"
    """
    if not tel or str(tel).strip() in ["", "None", "nan"]:
        return None

    num_str = str(tel).strip()

    # Essai 1 : parse direct si le numéro a déjà un "+"
    if num_str.startswith("+"):
        try:
            parsed = phonenumbers.parse(num_str, None)
            if phonenumbers.is_valid_number(parsed):
                region = phonenumbers.region_code_for_number(parsed)
                prefix = f"+{parsed.country_code}"
                return region or "FR", prefix
        except phonenumbers.NumberParseException:
            pass

    # Essai 2 : parse avec hint (ou "FR" par défaut)
    try:
        hint = (country_hint or "FR").upper()
        parsed = phonenumbers.parse(num_str, hint)
        if phonenumbers.is_valid_number(parsed):
            region = phonenumbers.region_code_for_number(parsed)
            prefix = f"+{parsed.country_code}"
            return region or hint, prefix
    except phonenumbers.NumberParseException:
        pass

    return None


def _detect_from_cp(cp: str, ville: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Étape 2 : Détecte le pays et le préfixe depuis le code postal.
    Retourne (code_pays, prefixe) ou None si échec.

    Exemple :
        cp="75008", ville="Paris" → pgeocode FR → pays: "FR", préfixe: "+33"
        cp="10115" → pgeocode DE → pays: "DE", préfixe: "+49"
    """
    if not cp or str(cp).strip() in ["", "None", "nan"]:
        return None

    cp_str = str(cp).strip()

    for country in SUPPORTED_COUNTRIES:
        nomi = _get_nominatim(country)
        if nomi is None:
            continue

        try:
            result = nomi.query_postal_code(cp_str)

            # Vérifie que pgeocode a trouvé quelque chose
            if result is None or pd.isna(result.place_name):
                continue

            # Si ville disponible, on vérifie la correspondance pour plus de fiabilité
            if ville and str(ville).strip() not in ["", "None", "nan"]:
                if str(ville).lower() not in str(result.place_name).lower():
                    continue

            # CP trouvé dans ce pays → on calcule le préfixe
            prefix_code = phonenumbers.country_code_for_region(country)
            if prefix_code:
                return country, f"+{prefix_code}"

        except Exception:
            continue

    return None


def extract_country_and_prefix(row: dict) -> Tuple[str, str]:
    """
    Fonction principale appelée pour chaque ligne du DataFrame.

    Priorité :
        1. phonenumbers depuis le tel (avec hint code_pays si présent)
        2. code_pays déjà présent (on cherche juste le préfixe)
        3. pgeocode depuis CP + ville
        4. fallback "FR" / "+33"

    Retourne toujours un tuple (code_pays, prefixe).
    """

    # Étape 1 — Détection depuis le numéro de téléphone
    tel = row.get("tel")
    provided_country = row.get("code_pays")
    if provided_country and str(provided_country).strip() in ["", "None", "nan"]:
        provided_country = None

    result = _detect_from_tel(
        str(tel) if tel else "",
        country_hint=str(provided_country) if provided_country else None
    )
    if result:
        return result

    # Étape 2 — Si code_pays fourni mais tel non détectable, on essaie de trouver le préfixe
    if provided_country:
        country_code = str(provided_country).strip().upper()
        prefix_code = phonenumbers.country_code_for_region(country_code)
        if prefix_code:
            return country_code, f"+{prefix_code}"

    # Étape 3 — Détection depuis le code postal + ville
    cp = row.get("code_postale")
    ville = row.get("ville")
    result = _detect_from_cp(
        str(cp) if cp else "",
        str(ville) if ville else ""
    )
    if result:
        return result

    # Étape 4 — Fallback France par défaut
    return "FR", "+33"