from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeadCreate(BaseModel):
    name: str
    intent: str = ""
    location: str = ""
    email: str = ""
    phone: str = ""
    budget: str = ""
    notes: str = ""


class LeadOut(LeadCreate):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
