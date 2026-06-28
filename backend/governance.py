"""Gov-ready application layer for NEXUS.

Application-level translation of the requested "Gov-Ready / Hybrid SaaS Tenant"
architecture (the Emergent platform already provides the K8s/VNET/WAF/CI-CD layer):

  - Multi-tenancy        : tenant_id on the user model + row-level isolation filters.
  - Granular RBAC        : role hierarchy user < analyst < tenant_admin < admin < owner.
  - Audit logging        : immutable trail of sensitive actions (db.audit_logs).
  - Brute-force defense   : Mongo-backed login lockout (db.login_attempts, TTL-cleaned).
  - Rate limiting        : lightweight sliding-window dependency for heavy endpoints.
"""
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Request

_db = None


def set_db(db):
    """Bind the active Motor database (called from the FastAPI startup event)."""
    global _db
    _db = db


# --------------------------------------------------------------------------- RBAC
# Higher level implicitly satisfies every lower-level requirement.
ROLE_LEVELS = {"user": 1, "analyst": 2, "tenant_admin": 3, "admin": 4, "owner": 5}
VALID_ROLES = list(ROLE_LEVELS.keys())
ADMIN_ROLES = ("admin", "owner")


def role_level(role: Optional[str]) -> int:
    return ROLE_LEVELS.get(role or "user", 0)


def is_admin(user: Optional[dict]) -> bool:
    """Platform-level administrator (sees across all tenants)."""
    return (user or {}).get("role") in ADMIN_ROLES


# ----------------------------------------------------------------------- Tenancy
DEFAULT_TENANT = "default"


def tenant_id_of(user: Optional[dict]) -> str:
    return (user or {}).get("tenant_id") or DEFAULT_TENANT


def tenant_scope(user: Optional[dict]) -> dict:
    """Row-level isolation filter. Platform admins/owners bypass scoping."""
    if is_admin(user):
        return {}
    return {"tenant_id": tenant_id_of(user)}


# ----------------------------------------------------------------------- Audit log
async def audit_log(action: str, user: Optional[dict] = None, request: Optional[Request] = None,
                    target: Optional[str] = None, meta: Optional[dict] = None,
                    status: str = "success"):
    """Append-only audit record. Never raises into the request path."""
    ip = _client_ip(request) if request is not None else None
    doc = {
        "action": action,
        "user_id": (user or {}).get("id"),
        "user_email": (user or {}).get("email"),
        "role": (user or {}).get("role"),
        "tenant_id": tenant_id_of(user) if user else None,
        "target": target,
        "meta": meta or {},
        "status": status,
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await _db.audit_logs.insert_one(doc)
    except Exception as e:
        # Never let auditing break a request, but a lost security-audit record must be visible.
        import logging
        logging.getLogger("nexus").error("audit_log write failed for %s: %s", action, e)


def audit_pub(r: dict) -> dict:
    return {"id": str(r.get("_id")), "action": r.get("action"), "user_email": r.get("user_email"),
            "role": r.get("role"), "tenant_id": r.get("tenant_id"), "target": r.get("target"),
            "meta": r.get("meta") or {}, "status": r.get("status"), "ip": r.get("ip"),
            "created_at": r.get("created_at")}


# ------------------------------------------------------------------ Brute force
MAX_FAILED = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOCKOUT_MIN = int(os.environ.get("LOGIN_LOCKOUT_MIN", "15"))


def _client_ip(request: Optional[Request]) -> str:
    if request is None:
        return "unknown"
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _attempt_id(request: Request, email: str) -> str:
    return f"{_client_ip(request)}:{(email or '').lower()}"


async def check_lockout(request: Request, email: str):
    rec = await _db.login_attempts.find_one({"_id": _attempt_id(request, email)})
    if not rec or rec.get("count", 0) < MAX_FAILED:
        return
    locked_until = rec.get("locked_until")
    if locked_until and locked_until > datetime.now(timezone.utc).isoformat():
        raise HTTPException(status_code=429,
            detail="Too many failed attempts — this login is temporarily locked. Try again later.")


async def record_failed_login(request: Request, email: str):
    locked_until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MIN)).isoformat()
    await _db.login_attempts.update_one(
        {"_id": _attempt_id(request, email)},
        {"$inc": {"count": 1},
         "$set": {"last_attempt": datetime.now(timezone.utc).isoformat(),
                  "locked_until": locked_until,
                  "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)}},
        upsert=True)


async def clear_login_attempts(request: Request, email: str):
    await _db.login_attempts.delete_one({"_id": _attempt_id(request, email)})


# ----------------------------------------------------------------- Rate limiting
_rl_buckets: dict = {}


def rate_limit(max_calls: int, window_sec: int):
    """Per-process sliding-window limiter keyed by client IP + route."""
    async def _dep(request: Request):
        key = f"{_client_ip(request)}:{request.url.path}"
        now = time.time()
        hits = [t for t in _rl_buckets.get(key, []) if now - t < window_sec]
        if len(hits) >= max_calls:
            raise HTTPException(status_code=429,
                detail="Rate limit exceeded — please slow down and retry shortly.")
        hits.append(now)
        _rl_buckets[key] = hits
        return True
    return _dep
