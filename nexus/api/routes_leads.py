"""Leads API routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from nexus.utils.validators import LeadModel
from nexus.database.repository import repository
from nexus.utils.logger import logger

router = APIRouter()


@router.post("/", response_model=LeadModel)
async def create_lead(lead: LeadModel):
    """Create new lead"""
    try:
        lead_data = lead.model_dump()
        created_lead = repository.create_lead(lead_data)
        return LeadModel.model_validate(created_lead)
    except Exception as e:
        logger.error(f"Failed to create lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[LeadModel])
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    min_quality: Optional[float] = Query(None, ge=0, le=100)
):
    """Get leads with pagination"""
    try:
        leads = repository.get_leads(skip=skip, limit=limit, min_quality=min_quality)
        return [LeadModel.model_validate(lead) for lead in leads]
    except Exception as e:
        logger.error(f"Failed to get leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lead_id}", response_model=LeadModel)
async def get_lead(lead_id: int):
    """Get lead by ID"""
    try:
        lead = repository.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return LeadModel.model_validate(lead)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{lead_id}", response_model=LeadModel)
async def update_lead(lead_id: int, lead: LeadModel):
    """Update lead"""
    try:
        updated_lead = repository.update_lead(lead_id, lead.model_dump())
        if not updated_lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return LeadModel.model_validate(updated_lead)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{lead_id}")
async def delete_lead(lead_id: int):
    """Delete lead"""
    try:
        deleted = repository.delete_lead(lead_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {"message": "Lead deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lead_id}/osint")
async def get_lead_osint(lead_id: int):
    """Get OSINT data for lead"""
    try:
        lead = repository.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        osint_data = repository.get_osint_data(lead_id)
        return [
            {
                "id": data.id,
                "data_type": data.data_type,
                "result": data.result_json,
                "confidence": data.confidence,
                "created_at": data.created_at
            }
            for data in osint_data
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get OSINT data: {e}")
        raise HTTPException(status_code=500, detail=str(e))