from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Enum as SQLEnum, BigInteger,Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum
from app.db.base import Base

class ReportType(str, enum.Enum):
    CALL = "call"
    SMS = "sms"
    EMAIL = "email"

class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class UserReport(Base):
    __tablename__ = "user_reports"
    
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    report_type = Column(SQLEnum(ReportType), nullable=False)
    content_hash = Column(String(64), nullable=False)
    phone_number = Column(String(20), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING)
    verified_by = Column(Integer, default=0)
    meta_data = Column(JSONB, default={})

class DetectionLog(Base):
    __tablename__ = "detection_logs"
    
    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    detection_type = Column(String(20), index=True, nullable=False)
    is_fraud = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    method_used = Column(String(20), nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String(20), nullable=True)
