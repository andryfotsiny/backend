# app/core/permissions.py

"""
Système de permissions par rôle
"""
from enum import Enum
from typing import List

class Permission(str, Enum):
    # Detection (PUBLIC/USER)
    CHECK_PHONE = "check:phone"
    ANALYZE_SMS = "analyze:sms"
    ANALYZE_EMAIL = "analyze:email"

    # Reports (USER)
    CREATE_REPORT = "report:create"
    VIEW_OWN_STATS = "stats:view_own"

    # Analytics (ORGANISATION)
    VIEW_GLOBAL_STATS = "analytics:stats"
    VIEW_TIMELINE = "analytics:timeline"
    VIEW_TRENDS = "analytics:trends"
    VIEW_LEADERBOARD = "analytics:leaderboard"

    # Admin (ADMIN)
    VIEW_ADMIN_DASHBOARD = "analytics:dashboard"
    CLEAR_CACHE = "admin:clear_cache"
    MANAGE_USERS = "admin:users"

# Permissions USER d'abord
USER_PERMISSIONS = [
    Permission.CHECK_PHONE,
    Permission.ANALYZE_SMS,
    Permission.ANALYZE_EMAIL,
    Permission.CREATE_REPORT,
    Permission.VIEW_OWN_STATS,
]

# Puis ORGANISATION (hérite USER)
ORGANISATION_PERMISSIONS = [
    *USER_PERMISSIONS,
    Permission.VIEW_GLOBAL_STATS,
    Permission.VIEW_TIMELINE,
    Permission.VIEW_TRENDS,
    Permission.VIEW_LEADERBOARD,
]

# Puis ADMIN (hérite ORGANISATION)
ADMIN_PERMISSIONS = [
    *ORGANISATION_PERMISSIONS,
    Permission.VIEW_ADMIN_DASHBOARD,
    Permission.CLEAR_CACHE,
    Permission.MANAGE_USERS,
]

# Mapping final
ROLE_PERMISSIONS: dict[str, List[Permission]] = {
    "USER": USER_PERMISSIONS,
    "ORGANISATION": ORGANISATION_PERMISSIONS,
    "ADMIN": ADMIN_PERMISSIONS
}

def has_permission(user_role: str, permission: Permission) -> bool:
    """Vérifie si un rôle a une permission"""
    return permission in ROLE_PERMISSIONS.get(user_role, [])