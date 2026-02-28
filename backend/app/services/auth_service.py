from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt
from app.core.security import pwd_context, hash_sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.report import UserReport, VerificationStatus
from app.core.config import settings
import uuid

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """Service d'authentification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash un mot de passe avec argon2"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifie un mot de passe et gère la re-hachage si nécessaire"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_email(email: str) -> str:
        """Hash email pour backup/compatibilité (SHA256)"""
        if not email:
            return None
        return hash_sha256(email.lower())

    @staticmethod
    def hash_phone(phone: str) -> str:
        """Hash téléphone pour backup/compatibilité (SHA256)"""
        return hash_sha256(phone)

    @staticmethod
    def create_access_token(user_id: str, role: str) -> Tuple[str, datetime]:
        """Crée un access token JWT"""
        expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": user_id,
            "exp": expires,
            "type": "access",
            "role": role,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expires

    @staticmethod
    def create_refresh_token(user_id: str, role: str) -> Tuple[str, datetime]:
        """Crée un refresh token JWT"""
        expires = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": user_id,
            "exp": expires,
            "type": "refresh",
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expires

    @staticmethod
    async def get_user_by_id(user_id: any, db: AsyncSession) -> Optional[User]:
        """Récupère un utilisateur par ID"""
        try:
            user_uuid = (
                user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(user_id)
            )
            result = await db.execute(select(User).where(User.user_id == user_uuid))
            return result.scalar_one_or_none()
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[str]:
        """Vérifie un token JWT et retourne user_id"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )

            user_id: str = payload.get("sub")
            token_type_claim: str = payload.get("type")

            if user_id is None or token_type_claim != token_type:
                return None

            return user_id

        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
        except Exception:
            return None

    @staticmethod
    async def register_user(
        email: str,
        password: str,
        phone: Optional[str],
        country_code: str,
        db: AsyncSession,
        role: str = "USER",
    ) -> User:
        """Enregistre un nouvel utilisateur"""

        existing = await db.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none():
            raise ValueError("EMAIL_ALREADY_EXISTS")

        user = User(
            user_id=uuid.uuid4(),
            email=email.lower(),
            phone=phone,
            email_hash=AuthService.hash_email(email),
            phone_hash=AuthService.hash_phone(phone) if phone else None,  # Optionnel
            password_hash=AuthService.hash_password(password),
            country_code=country_code,
            role=role,
            settings={
                "notifications": True,
                "language": "fr",
                "theme": "light",
                "auto_block": True,
            },
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def authenticate_user(
        email: str, password: str, db: AsyncSession
    ) -> Optional[User]:
        """Authentifie un utilisateur"""

        # Chercher par email en clair
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        if pwd_context.needs_update(user.password_hash):
            user.password_hash = AuthService.hash_password(password)

        user.last_active = datetime.utcnow()
        await db.commit()

        return user

    @staticmethod
    async def update_user(
        user_id: str,
        phone: Optional[str],
        country_code: Optional[str],
        settings: Optional[dict],
        db: AsyncSession,
    ) -> User:
        """Met à jour un utilisateur"""
        user = await AuthService.get_user_by_id(user_id, db)

        if not user:
            raise ValueError("USER_NOT_FOUND")

        if phone is not None:
            user.phone = phone  # ✅ Téléphone en clair
            user.phone_hash = AuthService.hash_phone(
                phone
            )  # Optionnel: mettre à jour hash

        if country_code is not None:
            user.country_code = country_code

        if settings is not None:
            user.settings.update(settings)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def change_password(
        user_id: str, current_password: str, new_password: str, db: AsyncSession
    ) -> bool:
        """Change le mot de passe utilisateur"""
        user = await AuthService.get_user_by_id(user_id, db)

        if not user:
            return False

        if not AuthService.verify_password(current_password, user.password_hash):
            return False

        user.password_hash = AuthService.hash_password(new_password)
        await db.commit()

        return True

    @staticmethod
    async def add_device_token(
        user_id: str, token: str, platform: str, db: AsyncSession
    ) -> bool:
        """Ajoute un token de device pour notifications push"""
        user = await AuthService.get_user_by_id(user_id, db)

        if not user:
            return False

        if token not in user.device_tokens:
            user.device_tokens.append(token)
            await db.commit()

        return True

    @staticmethod
    async def get_user_stats(user_id: str, db: AsyncSession) -> dict:
        """Récupère les statistiques utilisateur"""

        # Total signalements
        total_reports_result = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.user_id == user_id
            )
        )
        total_reports = total_reports_result.scalar() or 0

        # Signalements vérifiés
        verified_reports_result = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.user_id == user_id,
                UserReport.verification_status == VerificationStatus.VERIFIED,
            )
        )
        verified_reports = verified_reports_result.scalar() or 0

        # Signalements par type
        by_type_result = await db.execute(
            select(UserReport.report_type, func.count(UserReport.report_id))
            .where(UserReport.user_id == user_id)
            .group_by(UserReport.report_type)
        )

        reports_by_type = {row[0].value: row[1] for row in by_type_result}

        return {
            "total_reports": total_reports,
            "verified_reports": verified_reports,
            "pending_reports": total_reports - verified_reports,
            "reports_by_type": reports_by_type,
            "contribution_score": verified_reports * 10,
        }


# Instance globale
auth_service = AuthService()
