from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from datetime import datetime
from app.db.base import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nom = Column(String(100), index=True, nullable=True)
    nomination = Column(String(255), index=True)
    adresse = Column(String(500))
    code_postale = Column(String(10), index=True)
    ville = Column(String(100), index=True)
    prefixe = Column(String(10), index=True, nullable=True)
    code_pays = Column(String(3), index=True, nullable=True)
    tel = Column(String(20), unique=True, index=True)
    act = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
