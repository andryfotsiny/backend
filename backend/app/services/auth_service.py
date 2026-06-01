from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import jwt
from app.core.security import pwd_context, hash_sha256
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.report import UserReport, VerificationStatus
from app.core.config import settings
from app.services.redis_service import redis_service
from app.services.email_service import email_service
import uuid
import logging

logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


class AuthService:
    """Service d'authentification"""

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_email(email: str) -> str:
        if not email:
            return None
        return hash_sha256(email.lower())

    @staticmethod
    def hash_phone(phone: str) -> str:
        return hash_sha256(phone)

    @staticmethod
    def create_access_token(user_id: str, role: str) -> Tuple[str, datetime]:
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        jti = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "jti": jti,
            "exp": expires,
            "type": "access",
            "role": role,
            "iat": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expires

    @staticmethod
    def create_refresh_token(user_id: str, role: str) -> Tuple[str, datetime]:
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        jti = str(uuid.uuid4())
        payload = {
            "sub": user_id,
            "jti": jti,
            "exp": expires,
            "type": "refresh",
            "iat": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expires

    @staticmethod
    async def get_user_by_id(user_id: "str | uuid.UUID", db: AsyncSession) -> Optional[User]:
        try:
            user_uuid = (
                user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(user_id)
            )
            result = await db.execute(select(User).where(User.user_id == user_uuid))
            return result.scalar_one_or_none()
        except (ValueError, AttributeError):
            return None

    @staticmethod
    async def verify_token(token: str, token_type: str = "access") -> Optional[str]:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type_claim: str = payload.get("type")
            jti: str = payload.get("jti")

            if user_id is None or token_type_claim != token_type:
                return None

            if jti:
                try:
                    if await redis_service.is_token_blacklisted(jti):
                        return None
                except Exception as e:
                    # Si Redis est indisponible, on refuse le token par sécurité
                    # (fail-closed : mieux refuser un token valide que d'accepter un révoqué)
                    logger.warning("Redis unavailable for token check, denying: %s", e)
                    return None

            return user_id

        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
        except Exception:
            return None

    # ── Forgot / Reset Password ──────────────────────────────────────────────

    @staticmethod
    def create_password_reset_token(user_id: str) -> Tuple[str, datetime]:
        """Génère un JWT à usage unique pour la réinitialisation de mot de passe."""
        jti = str(uuid.uuid4())
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": user_id,
            "jti": jti,
            "exp": expires,
            "type": "password_reset",
            "iat": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expires

    @staticmethod
    async def verify_reset_token(token: str) -> Optional[str]:
        """Vérifie le token reset et retourne le user_id, ou None si invalide."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            user_id = payload.get("sub")
            jti = payload.get("jti")
            if not user_id or not jti:
                return None
            # Vérifier qu'il n'a pas déjà été utilisé (single-use via blacklist)
            if await redis_service.is_token_blacklisted(jti):
                return None
            return user_id
        except Exception:
            return None

    @staticmethod
    async def send_password_reset(email: str, db: AsyncSession) -> bool:
        """
        Envoie un email de réinitialisation de mot de passe.
        Retourne True même si l'email n'existe pas (sécurité anti-énumération).
        """
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            logger.info("forgot-password: email not found (silent) %s", email)
            return True  # Réponse volontairement identique pour éviter l'énumération

        token, _ = AuthService.create_password_reset_token(str(user.user_id))
        sent = await email_service.send_password_reset_email(email, token)
        if not sent:
            logger.error("forgot-password: email send failed to %s", email)
        return sent

    @staticmethod
    async def reset_password_with_token(token: str, new_password: str, db: AsyncSession) -> bool:
        """
        Réinitialise le mot de passe si le token est valide.
        Invalide le token après usage (single-use).
        """
        user_id = await AuthService.verify_reset_token(token)
        if not user_id:
            return False

        user = await AuthService.get_user_by_id(user_id, db)
        if not user:
            return False

        user.password_hash = AuthService.hash_password(new_password)
        await db.commit()

        # Blacklister le token pour usage unique
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                remaining = int(exp - datetime.now(timezone.utc).replace(tzinfo=None).timestamp())
                if remaining > 0:
                    await redis_service.blacklist_token(jti, remaining)
        except Exception:
            pass

        return True

    @staticmethod
    async def revoke_token(token: str):
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                now = datetime.now(timezone.utc).replace(tzinfo=None).timestamp()
                expire_seconds = int(exp - now)
                if expire_seconds > 0:
                    await redis_service.blacklist_token(jti, expire_seconds)
        except Exception as e:
            logger.error(f"Error revoking token: {e}")

    @staticmethod
    async def register_user(
        email: str,
        password: str,
        phone: Optional[str],
        country_code: str,
        db: AsyncSession,
        role: str = "USER",
        name: Optional[str] = None,  # ← NOUVEAU
    ) -> User:
        """Enregistre un nouvel utilisateur"""

        existing_email = await db.execute(select(User).where(User.email == email.lower()))
        if existing_email.scalar_one_or_none():
            raise ValueError("EMAIL_ALREADY_EXISTS")

        if phone:
            existing_phone = await db.execute(select(User).where(User.phone == phone))
            if existing_phone.scalar_one_or_none():
                raise ValueError("PHONE_ALREADY_EXISTS")

        user = User(
            user_id=uuid.uuid4(),
            email=email.lower(),
            phone=phone,
            name=name,  # ← NOUVEAU
            email_hash=AuthService.hash_email(email),
            phone_hash=AuthService.hash_phone(phone) if phone else None,
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
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        if pwd_context.needs_update(user.password_hash):
            user.password_hash = AuthService.hash_password(password)

        user.last_active = datetime.now(timezone.utc).replace(tzinfo=None)
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
        user = await AuthService.get_user_by_id(user_id, db)

        if not user:
            raise ValueError("USER_NOT_FOUND")

        if phone is not None:
            user.phone = phone
            user.phone_hash = AuthService.hash_phone(phone)

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
        user = await AuthService.get_user_by_id(user_id, db)

        if not user:
            return False

        if token not in user.device_tokens:
            user.device_tokens.append(token)
            await db.commit()

        return True

    @staticmethod
    async def get_user_stats(user_id: str, db: AsyncSession) -> dict:
        total_reports_result = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.user_id == user_id
            )
        )
        total_reports = total_reports_result.scalar() or 0

        verified_reports_result = await db.execute(
            select(func.count(UserReport.report_id)).where(
                UserReport.user_id == user_id,
                UserReport.verification_status == VerificationStatus.VERIFIED,
            )
        )
        verified_reports = verified_reports_result.scalar() or 0

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


auth_service = AuthService()