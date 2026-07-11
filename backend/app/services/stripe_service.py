"""Stripe integration for paid membership checkout and webhook handling."""
from __future__ import annotations

import hashlib
from typing import Any

import stripe

from . import config


def _stripe_client() -> stripe.StripeClient:
    key = config.stripe_secret_key()
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")
    return stripe.StripeClient(key, stripe_version=config.STRIPE_API_VERSION or None)


def checkout_idempotency_key(email: str, success_url: str, cancel_url: str, price_id: str) -> str:
    digest = hashlib.sha256(
        f"{email.strip().lower()}|{success_url}|{cancel_url}|{price_id}".encode("utf-8")
    ).hexdigest()
    return f"membership-checkout-{digest}"


def create_checkout_session(email: str, success_url: str, cancel_url: str, idempotency_key: str | None = None) -> str:
    """Create a Stripe Checkout session and return the session URL."""
    pid = config.price_id()
    if not pid:
        raise RuntimeError("PRICE_ID is not configured.")

    client = _stripe_client()
    session = client.v1.checkout.sessions.create(
        params={
            "mode": "subscription",
            "customer_email": email,
            "line_items": [{"price": pid, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
        },
        options={
            "idempotency_key": idempotency_key or checkout_idempotency_key(email, success_url, cancel_url, pid),
        },
    )
    if not session.url:
        raise RuntimeError("Stripe checkout session did not return a hosted URL.")
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str) -> Any:
    """Validate and parse an incoming Stripe webhook event."""
    secret = config.stripe_webhook_secret()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured.")
    return stripe.Webhook.construct_event(payload, sig_header, secret)


def get_subscription(subscription_id: str) -> Any:
    """Fetch a Stripe subscription object."""
    client = _stripe_client()
    return client.v1.subscriptions.retrieve(subscription_id)
