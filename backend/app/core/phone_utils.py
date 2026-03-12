import phonenumbers
import logging

logger = logging.getLogger(__name__)

def normalize_phone_number(phone: str, country_code: str = "MG") -> str:
    """
    Normalise un numéro de téléphone au format E.164.
    Par défaut, utilise Madagascar (MG) comme pays de référence.
    """
    if not phone:
        return ""
    
    try:
        cleaned_phone = "".join(filter(lambda x: x.isdigit() or x == "+", phone))
        
        parsed = phonenumbers.parse(cleaned_phone, country_code.upper())
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        
        return cleaned_phone
    except phonenumbers.NumberParseException as e:
        logger.warning(f"Could not parse phone number {phone}: {e}")
        return phone
