"""
Dependencies pour vérification rôles/permissions
"""
from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.api.deps.auth_deps import get_current_user
from app.core.roles import has_minimum_role
from app.core.permissions import Permission, has_permission

# ===== ROLE-BASED =====

def require_role(minimum_role: str):
    """
    Dependency factory : vérifie role minimum

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("ADMIN"))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if not has_minimum_role(current_user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Role {minimum_role} requis."
            )
        return current_user
    return role_checker

# ===== PERMISSION-BASED =====

def require_permission(permission: Permission):
    """
    Dependency factory : vérifie permission spécifique

    Usage:
        @router.post("/clear-cache", dependencies=[Depends(require_permission(Permission.CLEAR_CACHE))])
    """
    async def permission_checker(current_user: User = Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission {permission.value} requise"
            )
        return current_user
    return permission_checker

# ===== HELPERS =====

async def get_current_user_role(current_user: User = Depends(get_current_user)) -> str:
    """Retourne juste le role (pour logique conditionnelle)"""
    return current_user.role

# ===== SHORTCUTS =====

require_user = require_role("USER")
require_organisation = require_role("ORGANISATION")
require_admin = require_role("ADMIN")