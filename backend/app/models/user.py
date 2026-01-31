from sqlalchemy import Column, String, DateTime, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_hash = Column(String(64), unique=True, index=True, nullable=False)
    phone_hash = Column(String(64), unique=True, index=True, nullable=True)
    country_code = Column(String(3), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    settings = Column(JSONB, default={})
    device_tokens = Column(ARRAY(String), default=[])
    report_count = Column(Integer, default=0)
