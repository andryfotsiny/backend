from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BusinessBase(BaseModel):
    nomination: str
    adresse: Optional[str] = None
    code_postale: Optional[str] = None
    ville: Optional[str] = None
    tel: Optional[str] = None
    act: Optional[str] = None
    nom: Optional[str] = None
    code_pays: Optional[str] = None


class BusinessCreate(BusinessBase):
    pass


class Business(BusinessBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BusinessUpdate(BaseModel):
    nomination: Optional[str] = None
    adresse: Optional[str] = None
    code_postale: Optional[str] = None
    ville: Optional[str] = None
    tel: Optional[str] = None
    act: Optional[str] = None
    nom: Optional[str] = None
    code_pays: Optional[str] = None


class BusinessList(BaseModel):
    items: List[Business]
    total: int


class ImportResult(BaseModel):
    success_count: int
    skipped_count: int = 0
    failure_count: int
    errors: List[str] = []
