from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.auth_service import auth_service, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from app.schemas.auth import (
    UserRegister, UserLogin, Token, RefreshTokenRequest,
    UserResponse, PasswordChange, DeviceTokenCreate, AuthError
)
from app.models.user import User
from app.api.deps.auth_deps import get_current_user, verify_refresh_token, get_current_user_optional
from datetime import datetime
from typing import Optional

router = APIRouter()

# === REGISTER ===

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": AuthError, "description": "Email déjà utilisé"},
        403: {"model": AuthError, "description": "Permission refusée"},
        422: {"description": "Validation error"}
    }
)
async def register(
    user_data: UserRegister,
    current_admin: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Créer un nouveau compte utilisateur

    - **email**: Email valide (unique)
    - **password**: Min 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre
    - **phone**: Optionnel, format E.164 (+33612345678)
    - **country_code**: Code pays (FR, US, etc.)
    - **role**: Optionnel (USER par défaut, ORGANISATION/ADMIN nécessite admin)

    Retourne les informations utilisateur (sans mot de passe)
    """

    # Déterminer le rôle
    role = "USER"  # Par défaut

    # Si un rôle autre que USER est demandé
    if user_data.role and user_data.role != "USER":
        # Vérifier que la requête vient d'un ADMIN
        if not current_admin or current_admin.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul un administrateur peut créer des comptes ORGANISATION ou ADMIN"
            )

        # Valider le rôle demandé
        if user_data.role not in ["USER", "ORGANISATION", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rôle invalide. Valeurs autorisées: USER, ORGANISATION, ADMIN"
            )

        role = user_data.role

    try:
        user = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            phone=user_data.phone,
            country_code=user_data.country_code,
            role=role,
            db=db
        )
    except ValueError as e:
        if str(e) == "EMAIL_ALREADY_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
        raise

    # Retourner user info (sans password)
    return UserResponse(
        id=user.id,
        email=user_data.email,  # On retourne l'email en clair (pas le hash)
        phone=user_data.phone,
        country_code=user.country_code,
        role=user.role,
        created_at=user.created_at,
        last_active=user.last_active,
        total_reports=0,
        verified_reports=0
    )


# === LOGIN ===

@router.post(
    "/login",
    response_model=Token,
    responses={
        401: {"model": AuthError, "description": "Identifiants invalides"}
    }
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Se connecter et obtenir des tokens JWT

    - **email**: Email du compte
    - **password**: Mot de passe

    Retourne:
    - **access_token**: Token d'accès (30 min)
    - **refresh_token**: Token de renouvellement (7 jours)
    - Token contient le rôle utilisateur
    """

    # Authentifier
    user = await auth_service.authenticate_user(
        email=credentials.email,
        password=credentials.password,
        db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Créer tokens (avec role)
    access_token, access_expires = auth_service.create_access_token(user.id, user.role)
    refresh_token, refresh_expires = auth_service.create_refresh_token(user.id, user.role)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # en secondes
    )


# === REFRESH TOKEN ===

@router.post(
    "/refresh",
    response_model=Token,
    responses={
        401: {"model": AuthError, "description": "Refresh token invalide"}
    }
)
async def refresh_token(
    current_user: User = Depends(verify_refresh_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Renouveler l'access token avec un refresh token

    Headers:
    - **Authorization**: Bearer {refresh_token}

    Retourne de nouveaux tokens (avec role à jour)
    """

    # Créer nouveaux tokens (avec role actuel)
    access_token, _ = auth_service.create_access_token(current_user.id, current_user.role)
    refresh_token, _ = auth_service.create_refresh_token(current_user.id, current_user.role)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# === LOGOUT ===

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Se déconnecter

    Note: Avec JWT, le logout est côté client (supprimer le token)
    Cette route sert principalement à invalider le token côté serveur si implémenté
    """

    return {"message": "Déconnexion réussie"}


# === GET CURRENT USER (ME) ===

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtenir les informations de l'utilisateur connecté

    Headers:
    - **Authorization**: Bearer {access_token}

    Retourne le profil avec role et statistiques
    """

    # Récupérer stats
    stats = await auth_service.get_user_stats(current_user.id, db)

    return UserResponse(
        id=current_user.id,
        email="***@***",  # Masqué pour privacy (on a que le hash)
        phone="***" if current_user.phone_hash else None,
        country_code=current_user.country_code,
        role=current_user.role,
        created_at=current_user.created_at,
        last_active=current_user.last_active,
        total_reports=stats["total_reports"],
        verified_reports=stats["verified_reports"]
    )


# === CHANGE PASSWORD ===

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Changer le mot de passe

    - **current_password**: Mot de passe actuel
    - **new_password**: Nouveau mot de passe (min 8 caractères)
    """

    success = await auth_service.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )

    return {"message": "Mot de passe changé avec succès"}


# === ADD DEVICE TOKEN ===

@router.post("/device-token")
async def add_device_token(
    device_data: DeviceTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enregistrer un token de device pour notifications push

    - **token**: Token FCM (Android) ou APNS (iOS)
    - **platform**: "android" ou "ios"
    """

    success = await auth_service.add_device_token(
        user_id=current_user.id,
        token=device_data.token,
        platform=device_data.platform,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'enregistrer le token"
        )

    return {"message": "Token enregistré"}


# === GET USER STATS ===

@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtenir les statistiques de contribution de l'utilisateur

    - Total signalements
    - Signalements vérifiés
    - Signalements par type
    - Score de contribution

    Accessible à tous les utilisateurs authentifiés
    """

    stats = await auth_service.get_user_stats(current_user.id, db)

    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "stats": stats,
        "member_since": current_user.created_at.isoformat(),
        "last_active": current_user.last_active.isoformat()
    }


# === TEST PROTECTED ROUTE ===

@router.get("/test-protected")
async def test_protected(
    current_user: User = Depends(get_current_user)
):
    """
    Route de test pour vérifier que l'authentification fonctionne

    Nécessite un token valide
    """

    return {
        "message": "Accès autorisé !",
        "user_id": current_user.id,
        "role": current_user.role,
        "authenticated": True
    }