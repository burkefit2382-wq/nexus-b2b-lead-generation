from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models.lead import Lead
from ..schemas.lead import LeadCreate, LeadOut


router = APIRouter()


@router.post("/", response_model=LeadOut)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)) -> list[Lead]:
    return list(db.query(Lead).order_by(Lead.name.asc()).all())
