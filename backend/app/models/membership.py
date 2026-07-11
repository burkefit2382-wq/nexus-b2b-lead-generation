import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .lead import Base


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String)
    price_id: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="inactive", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=text("NOW()"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=text("NOW()"))
