"""Stripe integration for paid membership checkout and webhook handling."""
from __future__ import annotations

from typing import Any

import stripe

from . import config


def _stripe_client() -> stripe.Stripe:
    key = config.stripe_secret_key()
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")
    return stripe.Stripe(key, stripe_version=config.STRIPE_API_VERSION or None)


def create_checkout_session(email: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe Checkout session and return the session URL."""
    pid = config.price_id()
    if not pid:
        raise RuntimeError("PRICE_ID is not configured.")

    client = _stripe_client()
    session = client.checkout.sessions.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": pid, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> Any:
    """Validate and parse an incoming Stripe webhook event."""
    secret = config.stripe_webhook_secret()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured.")
    client = _stripe_client()
    return client.webhooks.construct_event(payload, sig_header, secret)


def get_subscription(subscription_id: str) -> Any:
    """Fetch a Stripe subscription object."""
    client = _stripe_client()
    return client.subscriptions.retrieve(subscription_id)
