import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
import bcrypt
from bson import ObjectId
from fastapi import Request, Response, HTTPException, Depends

import governance as gov
from core.db import db


JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(hours=12), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def set_auth_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=43200, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")

# ----- API key helpers (security: store only sha256 hash, show full key once) -----
def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

async def _user_from_api_key(raw_key: str) -> Optional[dict]:
    rec = await db.api_keys.find_one({"key_hash": hash_api_key(raw_key), "revoked": {"$ne": True}})
    if not rec:
        return None
    await db.api_keys.update_one({"_id": rec["_id"]},
                                 {"$set": {"last_used": datetime.now(timezone.utc).isoformat()},
                                  "$inc": {"calls": 1}})
    user = await db.users.find_one({"_id": ObjectId(rec["user_id"])})
    if not user:
        return None
    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    user["auth_method"] = "api_key"
    return user

async def get_current_user(request: Request) -> dict:
    # 1) API key auth (machine-to-machine)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        u = await _user_from_api_key(api_key)
        if u:
            return u
        raise HTTPException(status_code=401, detail="Invalid API key")
    # 2) JWT cookie / bearer (interactive)
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user.pop("_id"))
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ----- Role-based access control -----
def require_role(*roles: str):
    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _checker

require_admin = require_role("admin", "owner")

def require_min_role(min_role: str):
    """Granular RBAC: pass if the user's role level >= min_role's level."""
    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if gov.role_level(user.get("role")) < gov.role_level(min_role):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _checker
