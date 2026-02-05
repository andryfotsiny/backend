from typing import Optional

from pydantic import BaseModel, Field

from app.models.fraud import FraudType


class SMSReportCreate(BaseModel):
    content: str = Field(..., max_length=500, description="Contenu SMS frauduleux")
    sender: str = Field(..., description="Numéro expéditeur")
    fraud_category: str = Field(..., description="Catégorie (phishing, scam, etc.)")
    comment: Optional[str] = Field(None, max_length=500)
    user_id: Optional[str] = None

class EmailReportCreate(BaseModel):
    sender: str = Field(..., description="Email expéditeur")
    domain: str = Field(..., description="Domaine (ex: fake-bank.com)")
    phishing_type: str = Field(..., description="Type phishing (banking, delivery, etc.)")
    comment: Optional[str] = Field(None, max_length=500)
    user_id: Optional[str] = None

# Dans app/schemas/reports.py, ligne ~18
class ReportResponse(BaseModel):
    success: bool
    report_id: str  # ✅ Changer int en str (car c'est un UUID)
    message: str
    total_reports: int
    verified: bool
    auto_added: bool = False

class PhoneReportCreate(BaseModel):
    phone: str = Field(..., description="Numéro à signaler (format E.164)")
    country: str = Field(..., max_length=2, description="Code pays (FR, US, etc.)")
    fraud_type: FraudType = Field(..., description="Type de fraude")
    comment: Optional[str] = Field(None, max_length=500, description="Commentaire optionnel")
    user_id: Optional[str] = Field(None, description="ID utilisateur (optionnel pour MVP)")
