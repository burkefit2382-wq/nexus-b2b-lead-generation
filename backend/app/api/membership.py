"""Membership API: Stripe checkout, webhook handler, and status lookup."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models.membership import Membership
from ..schemas.membership import CheckoutRequest, CheckoutResponse, MembershipStatus
from ..services import config
from ..services import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(payload: CheckoutRequest, db: Session = Depends(get_db)) -> CheckoutResponse:
    """Create a Stripe Checkout session for a new paid membership."""
    if not config.stripe_configured():
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    base = config.public_base_url().rstrip("/")
    success_url = f"{base}/membership/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base}/membership/cancel"

    try:
        url = stripe_service.create_checkout_session(payload.email, success_url, cancel_url)
    except stripe.StripeError as exc:
        logger.error("Stripe checkout error: %s", exc)
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message or str(exc)}") from exc

    # Upsert a pending membership record so we have the email on file.
    membership = db.query(Membership).filter(Membership.email == payload.email).first()
    if not membership:
        membership = Membership(email=payload.email, status="pending")
        db.add(membership)
        db.commit()

    return CheckoutResponse(checkout_url=url)


@router.post("/webhook", status_code=200)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Handle Stripe webhook events (checkout.session.completed, customer.subscription.*)."""
    sig = request.headers.get("stripe-signature", "")
    body = await request.body()

    try:
        event = stripe_service.construct_webhook_event(body, sig)
    except (stripe.SignatureVerificationError, RuntimeError) as exc:
        logger.warning("Webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid webhook signature.") from exc

    event_type: str = event["type"]
    data_obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, data_obj)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _handle_subscription_change(db, data_obj)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"received": "ok"}


@router.get("/status", response_model=MembershipStatus)
def membership_status(email: str, db: Session = Depends(get_db)) -> Membership:
    """Return membership status for a given email address."""
    membership = db.query(Membership).filter(Membership.email == email).first()
    if not membership:
        raise HTTPException(status_code=404, detail="No membership found for this email.")
    return membership


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _handle_checkout_completed(db: Session, session_obj: dict[str, Any]) -> None:
    email = session_obj.get("customer_email") or (session_obj.get("customer_details") or {}).get("email")
    if not email:
        logger.warning("checkout.session.completed missing email — skipping.")
        return

    subscription_id = session_obj.get("subscription")
    customer_id = session_obj.get("customer")

    membership = db.query(Membership).filter(Membership.email == email).first()
    if not membership:
        membership = Membership(email=email)
        db.add(membership)

    membership.stripe_customer_id = customer_id
    membership.stripe_subscription_id = subscription_id
    membership.status = "active"
    membership.price_id = config.price_id()
    membership.updated_at = datetime.now(timezone.utc)

    # Fetch period end from the subscription object if available.
    if subscription_id:
        try:
            sub = stripe_service.get_subscription(subscription_id)
            period_end = sub.get("current_period_end")
            if period_end:
                membership.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
        except stripe.StripeError as exc:
            logger.warning("Could not fetch subscription %s: %s", subscription_id, exc)

    db.commit()
    logger.info("Membership activated for %s", email)


def _handle_subscription_change(db: Session, sub_obj: dict[str, Any]) -> None:
    subscription_id = sub_obj.get("id")
    status = sub_obj.get("status", "inactive")
    period_end = sub_obj.get("current_period_end")

    membership = db.query(Membership).filter(Membership.stripe_subscription_id == subscription_id).first()
    if not membership:
        logger.warning("No membership found for subscription %s", subscription_id)
        return

    membership.status = "active" if status in ("active", "trialing") else "inactive"
    if period_end:
        membership.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
    membership.updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Membership %s status -> %s", membership.email, membership.status)
