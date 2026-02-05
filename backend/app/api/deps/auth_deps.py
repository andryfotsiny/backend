from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.services.auth_service import auth_service
from app.models.user import User

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency pour récupérer l'utilisateur courant depuis le JWT
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Accepter access ET refresh tokens
    user_id = auth_service.verify_token(token, token_type="access")
    if user_id is None:
        # Essayer avec refresh token
        user_id = auth_service.verify_token(token, token_type="refresh")

    if user_id is None:
        raise credentials_exception

    user = await auth_service.get_user_by_id(user_id, db)

    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency pour utilisateur optionnel

    Retourne User si token valide, None sinon (pas d'erreur)

    Usage:
        @router.get("/public-or-private")
        async def route(current_user: Optional[User] = Depends(get_current_user_optional)):
            if current_user:
                return {"message": f"Hello {current_user.id}"}
            return {"message": "Hello anonymous"}
    """

    if credentials is None:
        return None

    token = credentials.credentials
    user_id = auth_service.verify_token(token, token_type="access")

    if user_id is None:
        return None

    user = await auth_service.get_user_by_id(user_id, db)
    return user


async def verify_refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency pour vérifier refresh token

    Usage dans endpoint /refresh
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    user_id = auth_service.verify_token(token, token_type="refresh")

    if user_id is None:
        raise credentials_exception

    user = await auth_service.get_user_by_id(user_id, db)

    if user is None:
        raise credentials_exception

    return user