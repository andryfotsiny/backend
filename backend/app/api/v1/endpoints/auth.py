from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.auth_service import auth_service, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserResponse,
    PasswordChange,
    DeviceTokenCreate,
    AuthError,
)
from app.models.user import User
from app.api.deps.auth_deps import (
    get_current_user,
    verify_refresh_token,
    get_current_user_optional,
    security,
)
from typing import Optional

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un nouveau compte utilisateur",
    responses={
        201: {"description": "Compte créé avec succès"},
        400: {"model": AuthError, "description": "Données invalides ou email déjà utilisé"},
        403: {"model": AuthError, "description": "Permission refusée"},
        422: {"description": "Erreur de validation des champs"},
    },
)
async def register(
    user_data: UserRegister,
    current_admin: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    role = "USER"

    if user_data.role and user_data.role != "USER":
        if not current_admin or current_admin.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seul un administrateur peut créer des comptes ORGANISATION ou ADMIN",
            )

        if user_data.role not in ["USER", "ORGANISATION", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rôle invalide. Valeurs autorisées: USER, ORGANISATION, ADMIN",
            )

        role = user_data.role

    try:
        user = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            phone=user_data.phone,
            country_code=user_data.country_code,
            role=role,
            name=user_data.name,  # ← NOUVEAU
            db=db,
        )
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "EMAIL_ALREADY_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé",
            )
        if error_msg == "PHONE_ALREADY_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce numéro de téléphone est déjà utilisé",
            )
        raise

    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        name=user.name,  # ← NOUVEAU
        country_code=user.country_code,
        role=user.role,
        created_at=user.created_at,
        last_active=user.last_active,
        total_reports=0,
        verified_reports=0,
    )


@router.post(
    "/login",
    response_model=Token,
    responses={401: {"model": AuthError, "description": "Identifiants invalides"}},
)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(
        email=credentials.email, password=credentials.password, db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, _ = auth_service.create_access_token(user.id, user.role)
    refresh_token, _ = auth_service.create_refresh_token(user.id, user.role)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=Token,
    responses={401: {"model": AuthError, "description": "Refresh token invalide"}},
)
async def refresh_token(
    current_user: User = Depends(verify_refresh_token),
    db: AsyncSession = Depends(get_db),
):
    access_token, _ = auth_service.create_access_token(
        current_user.id, current_user.role
    )
    refresh_token, _ = auth_service.create_refresh_token(
        current_user.id, current_user.role
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: Optional[str] = Depends(security),
):
    if credentials:
        await auth_service.revoke_token(credentials.credentials)
    return {"message": "Déconnexion réussie"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stats = await auth_service.get_user_stats(current_user.id, db)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        phone=current_user.phone,
        name=current_user.name,  # ← NOUVEAU
        country_code=current_user.country_code,
        role=current_user.role,
        created_at=current_user.created_at,
        last_active=current_user.last_active,
        total_reports=stats["total_reports"],
        verified_reports=stats["verified_reports"],
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await auth_service.change_password(
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        db=db,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )

    return {"message": "Mot de passe changé avec succès"}


@router.post("/device-token")
async def add_device_token(
    device_data: DeviceTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await auth_service.add_device_token(
        user_id=current_user.id,
        token=device_data.token,
        platform=device_data.platform,
        db=db,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'enregistrer le token",
        )

    return {"message": "Token enregistré"}


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stats = await auth_service.get_user_stats(current_user.id, db)

    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "stats": stats,
        "member_since": current_user.created_at.isoformat(),
        "last_active": current_user.last_active.isoformat(),
    }


@router.get("/test-protected")
async def test_protected(current_user: User = Depends(get_current_user)):
    return {
        "message": "Accès autorisé !",
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "authenticated": True,
    }