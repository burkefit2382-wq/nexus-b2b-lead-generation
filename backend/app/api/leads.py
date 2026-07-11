import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models.lead import Lead
from ..schemas.lead import LeadCreate, LeadOut
from ..services.hubspot import HubSpotExportError, hubspot_access_token, hubspot_contact_properties, upsert_hubspot_contact


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=LeadOut)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    token = hubspot_access_token()
    if token:
        try:
            properties = hubspot_contact_properties(payload.model_dump())
            upsert_hubspot_contact(token, properties)
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HubSpotExportError as exc:
            logger.warning(
                "HubSpot sync failed for lead email=%s company=%s: %s",
                payload.email or "",
                payload.name,
                exc,
            )
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=list[LeadOut])
def list_leads(db: Session = Depends(get_db)) -> list[Lead]:
    return list(db.query(Lead).order_by(Lead.name.asc()).all())
