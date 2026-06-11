"""Data validators for NEXUS"""
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


class LeadModel(BaseModel):
    """Lead data model"""
    company_name: str = Field(..., min_length=1)
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "US"
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    revenue: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    reviews_count: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    source: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0, le=100)

    @validator('website')
    def validate_website(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v:
            v = re.sub(r'[^\d+]', '', v)
        return v


class OSINTResult(BaseModel):
    """OSINT enrichment result"""
    lead_id: int
    data_type: str
    result: dict
    confidence: float = Field(ge=0, le=1)
    timestamp: str


class AISummary(BaseModel):
    """AI-generated summary"""
    lead_id: int
    summary: str
    insights: list[str]
    score: float = Field(ge=0, le=100)
    generated_at: str