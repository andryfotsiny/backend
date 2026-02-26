"""
Définition des rôles et hiérarchie
"""
from enum import Enum

class Role(str, Enum):
    USER = "USER"
    ORGANISATION = "ORGANISATION"
    ADMIN = "ADMIN"

ROLE_HIERARCHY = {
    "ADMIN": 3,
    "ORGANISATION": 2,
    "USER": 1
}

def has_minimum_role(user_role: str, required_role: str) -> bool:
    """Vérifie si user a au moins le role requis"""
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)