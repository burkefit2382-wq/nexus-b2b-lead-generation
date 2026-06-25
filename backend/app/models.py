from pydantic import BaseModel, EmailStr
from typing import Optional


class Lead(BaseModel):
    id: str
    company: str
    contact_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    score: int = 0


class LeadSearchRequest(BaseModel):
    company_name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    limit: int = 20


class LeadSearchResponse(BaseModel):
    leads: list[Lead]
    total: int
    query: str


class NotifyRequest(BaseModel):
    to: str
    leads: list[Lead]
    query: str


class NotifyResponse(BaseModel):
    message_id: str
    recipient: str
