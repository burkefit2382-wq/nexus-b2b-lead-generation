from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class CheckoutRequest(BaseModel):
    email: EmailStr


class CheckoutResponse(BaseModel):
    checkout_url: str


class MembershipStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: str
    price_id: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_end: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
