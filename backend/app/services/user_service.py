from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
import uuid
from app.models.user import User
from app.schemas.user import UserUpdate
from app.services.auth_service import auth_service

class UserService:
    async def get_all_users(self, db: AsyncSession) -> List[User]:
        """Récupère tous les utilisateurs"""
        result = await db.execute(select(User).order_by(User.created_at.desc()))
        return result.scalars().all()

    async def get_user_by_id(self, user_id: str, db: AsyncSession) -> Optional[User]:
        """Récupère un utilisateur par son ID"""
        try:
            user_uuid = uuid.UUID(user_id)
            result = await db.execute(select(User).where(User.user_id == user_uuid))
            return result.scalar_one_or_none()
        except (ValueError, AttributeError):
            return None

    async def update_user(self, user_id: str, obj_in: UserUpdate, db: AsyncSession) -> Optional[User]:
        """Met à jour un utilisateur et ses hashes si nécessaire"""
        user = await self.get_user_by_id(user_id, db)
        if not user:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Mise à jour des données
        for field, value in update_data.items():
            setattr(user, field, value)
            
            # Recalculer les hashes si email ou phone changent
            if field == "email":
                user.email_hash = auth_service.hash_email(value)
            elif field == "phone":
                user.phone_hash = auth_service.hash_phone(value)

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def delete_user(self, user_id: str, db: AsyncSession) -> bool:
        """Supprime un utilisateur"""
        user = await self.get_user_by_id(user_id, db)
        if not user:
            return False
        
        await db.delete(user)
        await db.commit()
        return True

user_service = UserService()
