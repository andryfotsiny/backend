from sqlalchemy import Column, String, DateTime, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.db.base import Base
from enum import Enum
from sqlalchemy.orm import validates
from app.core.security import hash_sha256


class UserRole(str, Enum):
    USER = "USER"
    ORGANISATION = "ORGANISATION"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Email et téléphone en CLAIR (nouveaux)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)

    # Hash gardés pour compatibilité / backup (optionnel)
    email_hash = Column(String(64), unique=True, index=True, nullable=True)
    phone_hash = Column(String(64), unique=True, index=True, nullable=True)

    password_hash = Column(String(255), nullable=False)
    country_code = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSONB, default={})
    device_tokens = Column(ARRAY(String), default=[])
    report_count = Column(Integer, default=0)
    role = Column(String(20), default="USER", nullable=False)

    # Propriété pour compatibilité
    @property
    def id(self):
        return str(self.user_id)

    @validates("email")
    def validate_email(self, key, email):
        if email:
            self.email_hash = hash_sha256(email.lower())
        return email

    @validates("phone")
    def validate_phone(self, key, phone):
        if phone:
            self.phone_hash = hash_sha256(phone)
        return phone
