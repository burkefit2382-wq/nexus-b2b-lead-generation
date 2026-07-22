"""Sentry observability integration.

Sentry is fully optional: when ``SENTRY_DSN`` is unset the SDK is never
initialised and all helper functions are no-ops.  The app runs in exactly the
same way locally and in CI without any DSN configured.

Sensitive fields are scrubbed from every event via the ``before_send`` hook so
that secrets (Stripe keys, HubSpot tokens, raw payment payloads, JWT secrets,
etc.) are never transmitted to Sentry.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keys that must never appear in Sentry events (headers, extra data, tags,
# request bodies, environment, etc.).  Checked case-insensitively.
# ---------------------------------------------------------------------------
_SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "secret",
    "password",
    "token",
    "api_key",
    "apikey",
    "stripe",
    "hubspot",
    "resend",
    "jwt",
    "authorization",
    "cookie",
    "card",
    "cvv",
    "ssn",
    "r2_access",
    "r2_secret",
    "database_url",
)

_SCRUBBED = "[Filtered]"


def _is_sensitive_key(key: str) -> bool:
    """Return True if *key* looks like it could contain a secret value."""
    lower = key.lower()
    return any(fragment in lower for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _scrub_dict(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Replace values for sensitive keys in *data* with ``[Filtered]``."""
    if not isinstance(data, dict):
        return data
    return {
        key: (_SCRUBBED if _is_sensitive_key(str(key)) else _scrub_dict(value) if isinstance(value, dict) else value)
        for key, value in data.items()
    }


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:  # noqa: ARG001
    """Sentry ``before_send`` hook — scrub sensitive data before transmission."""
    # Scrub HTTP request headers and environment.
    request = event.get("request") or {}
    if isinstance(request, dict):
        if "headers" in request:
            request["headers"] = _scrub_dict(request["headers"])
        if "env" in request:
            request["env"] = _scrub_dict(request["env"])
        # Never send raw request body (may contain card/PII data).
        if "data" in request:
            request["data"] = _SCRUBBED
        event["request"] = request

    # Scrub extra context and tags that might include secrets.
    if "extra" in event:
        event["extra"] = _scrub_dict(event["extra"])

    return event


def init() -> None:
    """Initialise the Sentry SDK if ``SENTRY_DSN`` is configured.

    Safe to call multiple times — subsequent calls when DSN is absent are
    no-ops.  When ``SENTRY_DSN`` is set the SDK is configured with:

    * Performance tracing at the rate controlled by
      ``SENTRY_TRACES_SAMPLE_RATE`` (default 0.1).
    * The ``before_send`` PII-scrubbing hook.
    * ``environment`` and ``release`` tagging.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.debug("SENTRY_DSN not set — Sentry disabled.")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("sentry-sdk is not installed — Sentry disabled.")
        return

    traces_sample_rate = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    environment = os.environ.get("SENTRY_ENVIRONMENT", "production")
    release = os.environ.get("SENTRY_RELEASE", None)

    kwargs: dict[str, Any] = dict(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        before_send=before_send,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        # Do not send default PII (IPs, user-agents) automatically.
        send_default_pii=False,
    )
    if release:
        kwargs["release"] = release

    # profiles_sample_rate is supported in sentry-sdk >= 1.18; guard against
    # older versions gracefully.
    profiles_sample_rate = float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.0"))
    if profiles_sample_rate > 0:
        kwargs["profiles_sample_rate"] = profiles_sample_rate

    sentry_sdk.init(**kwargs)
    logger.info("Sentry initialised (environment=%s, traces_sample_rate=%s).", environment, traces_sample_rate)


def capture_integration_error(
    exc: BaseException,
    integration: str,
    *,
    extra: dict[str, Any] | None = None,
) -> None:
    """Capture *exc* in Sentry and tag it with the originating *integration*.

    This is a **no-op** when Sentry is not initialised (i.e. DSN is absent).

    Args:
        exc: The exception to report.
        integration: Human-readable integration name, e.g. ``"stripe"``,
            ``"hubspot"``, or ``"resend"``.
        extra: Additional (non-sensitive) key/value pairs to attach to the
            event for easier filtering in the Sentry dashboard.
    """
    try:
        import sentry_sdk
    except ImportError:
        return

    with sentry_sdk.new_scope() as scope:
        scope.set_tag("integration", integration)
        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)
        sentry_sdk.capture_exception(exc)
