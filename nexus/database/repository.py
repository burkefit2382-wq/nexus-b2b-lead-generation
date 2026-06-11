"""Database repository for NEXUS"""
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import json
from nexus.database.models import Base, Lead, OSINTData, AISummary, ScrapeTask
from nexus.config import settings
from nexus.utils.logger import logger


class Repository:
    """Database repository"""

    def __init__(self):
        self.engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO
        )
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        Base.metadata.create_all(self.engine)
        logger.info("Database initialized")

    def get_session(self) -> Session:
        """Get database session"""
        return Session(self.engine)

    # Lead CRUD
    def create_lead(self, lead_data: Dict) -> Lead:
        """Create new lead"""
        with self.get_session() as session:
            lead = Lead(**lead_data)
            session.add(lead)
            session.commit()
            session.refresh(lead)
            logger.info(f"Created lead: {lead.company_name}")
            return lead

    def get_lead(self, lead_id: int) -> Optional[Lead]:
        """Get lead by ID"""
        with self.get_session() as session:
            return session.query(Lead).filter(Lead.id == lead_id).first()

    def get_leads(
        self,
        skip: int = 0,
        limit: int = 100,
        min_quality: Optional[float] = None
    ) -> List[Lead]:
        """Get leads with pagination"""
        with self.get_session() as session:
            query = session.query(Lead)

            if min_quality:
                query = query.filter(Lead.quality_score >= min_quality)

            return query.offset(skip).limit(limit).all()

    def update_lead(self, lead_id: int, updates: Dict) -> Optional[Lead]:
        """Update lead"""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                for key, value in updates.items():
                    setattr(lead, key, value)
                session.commit()
                session.refresh(lead)
            return lead

    def delete_lead(self, lead_id: int) -> bool:
        """Delete lead"""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                session.delete(lead)
                session.commit()
                return True
            return False

    # OSINT Data
    def create_osint_data(self, lead_id: int, data_type: str, result: Dict, confidence: float = 0.0) -> OSINTData:
        """Create OSINT data record"""
        with self.get_session() as session:
            osint_data = OSINTData(
                lead_id=lead_id,
                data_type=data_type,
                result_json=json.dumps(result),
                confidence=confidence
            )
            session.add(osint_data)
            session.commit()
            session.refresh(osint_data)
            return osint_data

    def get_osint_data(self, lead_id: int) -> List[OSINTData]:
        """Get OSINT data for lead"""
        with self.get_session() as session:
            return session.query(OSINTData).filter(OSINTData.lead_id == lead_id).all()

    # AI Summaries
    def create_ai_summary(
        self,
        lead_id: int,
        summary: str,
        insights: List[str],
        score: float
    ) -> AISummary:
        """Create AI summary"""
        with self.get_session() as session:
            ai_summary = AISummary(
                lead_id=lead_id,
                summary=summary,
                insights_json=json.dumps(insights),
                score=score
            )
            session.add(ai_summary)
            session.commit()
            session.refresh(ai_summary)
            return ai_summary

    def get_ai_summary(self, lead_id: int) -> Optional[AISummary]:
        """Get AI summary for lead"""
        with self.get_session() as session:
            return session.query(AISummary).filter(AISummary.lead_id == lead_id).first()

    # Scrape Tasks
    def create_scrape_task(self, task_type: str, query: str) -> ScrapeTask:
        """Create scrape task"""
        with self.get_session() as session:
            task = ScrapeTask(task_type=task_type, query=query)
            session.add(task)
            session.commit()
            session.refresh(task)
            return task

    def update_scrape_task(
        self,
        task_id: int,
        status: str,
        results_count: int = 0,
        error_message: Optional[str] = None
    ) -> Optional[ScrapeTask]:
        """Update scrape task"""
        with self.get_session() as session:
            task = session.query(ScrapeTask).filter(ScrapeTask.id == task_id).first()
            if task:
                task.status = status
                task.results_count = results_count
                task.error_message = error_message
                session.commit()
                session.refresh(task)
            return task

    def get_scrape_tasks(self, status: Optional[str] = None) -> List[ScrapeTask]:
        """Get scrape tasks"""
        with self.get_session() as session:
            query = session.query(ScrapeTask)
            if status:
                query = query.filter(ScrapeTask.status == status)
            return query.all()


# Global repository instance
repository = Repository()