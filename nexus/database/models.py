"""SQLAlchemy database models"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Lead(Base):
    """Lead model"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    website = Column(String(512))
    phone = Column(String(50))
    email = Column(String(255))
    address = Column(String(512))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100), default="US")
    industry = Column(String(100))
    employee_count = Column(String(50))
    revenue = Column(String(50))
    rating = Column(Float)
    reviews_count = Column(Integer)
    description = Column(Text)
    source = Column(String(100))
    quality_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OSINTData(Base):
    """OSINT enrichment data"""
    __tablename__ = "osint_data"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, nullable=False)
    data_type = Column(String(50), nullable=False)  # email, phone, domain, breach
    result_json = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AISummary(Base):
    """AI-generated summaries"""
    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, nullable=False)
    summary = Column(Text)
    insights_json = Column(Text)
    score = Column(Float)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


class ScrapeTask(Base):
    """Scraping task tracking"""
    __tablename__ = "scrape_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(50), nullable=False)  # google_maps, linkedin, custom
    query = Column(String(512))
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    results_count = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))