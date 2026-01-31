from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum
from app.db.base import Base

class FraudType(str, enum.Enum):
    SPAM = "spam"
    SCAM = "scam"
    ROBOCALL = "robocall"
    PHISHING = "phishing"
    SPOOFING = "spoofing"

class FraudulentNumber(Base):
    __tablename__ = "fraudulent_numbers"
    
    phone_number = Column(String(20), primary_key=True, index=True)
    country_code = Column(String(3), index=True, nullable=False)
    fraud_type = Column(SQLEnum(FraudType), nullable=False)
    confidence_score = Column(Float, nullable=False)
    report_count = Column(Integer, default=1)
    verified = Column(Boolean, default=False)
    first_reported = Column(DateTime, default=datetime.utcnow)
    last_reported = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSONB, default={})
    source = Column(String(50), default="crowdsource")

class FraudulentSMSPattern(Base):
    __tablename__ = "fraudulent_sms_patterns"
    
    pattern_id = Column(Integer, primary_key=True, autoincrement=True)
    regex_pattern = Column(String, nullable=True)
    keywords = Column(JSONB, default=[])
    fraud_category = Column(String(50), index=True)
    language = Column(String(5), default="fr")
    severity = Column(Integer, default=5)
    detection_count = Column(Integer, default=0)
    false_positive_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class FraudulentDomain(Base):
    __tablename__ = "fraudulent_domains"
    
    domain = Column(String(255), primary_key=True, index=True)
    phishing_type = Column(String(50))
    first_seen = Column(DateTime, default=datetime.utcnow)
    blocked_count = Column(Integer, default=0)
    spf_valid = Column(Boolean, default=False)
    dkim_valid = Column(Boolean, default=False)
    dmarc_policy = Column(String(20))
    reputation_score = Column(Float, default=0.0)
