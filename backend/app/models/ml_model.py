from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from datetime import datetime
from app.db.base import Base

class MLModelVersion(Base):
    __tablename__ = "ml_model_versions"
    
    version_id = Column(Integer, primary_key=True, autoincrement=True)
    model_type = Column(String(50), nullable=False)
    training_date = Column(DateTime, default=datetime.utcnow)
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    training_samples = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=False)
    model_path = Column(String(255), nullable=False)
