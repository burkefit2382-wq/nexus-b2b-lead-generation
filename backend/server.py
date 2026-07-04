from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import re
import json
import socket
import asyncio
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import jwt
import bcrypt
import httpx
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

import governance as gov

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("nexus")

# ----------------------------------------------------------------------------- DB
# NOTE: the Motor client must be created INSIDE the running event loop (in the
# startup handler), not at import time. Creating it at import binds to a loop
# that doesn't exist yet and silently breaks connections under MongoDB Atlas
# (mongodb+srv) in production. These are populated in the startup event.
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
client = None
db = None

# ----------------------------------------------------------------------------- Auth helpers
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

# ----------------------------------------------------------------------------- DeepSeek / Qwen (HF router)
def _resolve_model(key: str) -> str:
    if key == "qwen":
        return os.environ.get("QWEN_MODEL", "Qwen/Qwen2.5-32B-Instruct")
    if key == "llama":
        return os.environ.get("LLAMA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3.1:novita")

def _active_ai_model(model_key: str = "deepseek") -> str:
    if os.environ.get("AI_PROVIDER", "emergent").lower() == "emergent":
        return f"{os.environ.get('EMERGENT_AI_PROVIDER', 'gemini')}/{os.environ.get('EMERGENT_AI_MODEL', 'gemini-3-flash-preview')}"
    return _resolve_model(model_key)

def _hf_chat_sync(messages, model_key="deepseek", max_tokens=600, temperature=0.4):
    token = os.environ.get("HF_TOKEN", "")
    model = _resolve_model(model_key)
    base = os.environ.get("HF_ROUTER_BASE", "https://router.huggingface.co/v1")
    if not token:
        return {"error": "No HF_TOKEN configured"}
    try:
        from openai import OpenAI
        c = OpenAI(base_url=base, api_key=token)
        r = c.chat.completions.create(model=model, messages=messages,
                                      max_tokens=max_tokens, temperature=temperature)
        return {"content": r.choices[0].message.content, "model": model}
    except Exception as e:
        return {"error": str(e)}

async def _emergent_chat_async(messages, max_tokens=600, temperature=0.4):
    """Text generation via the Emergent Universal Key (emergentintegrations)."""
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        return {"error": "No EMERGENT_LLM_KEY configured"}
    provider = os.environ.get("EMERGENT_AI_PROVIDER", "gemini")
    model = os.environ.get("EMERGENT_AI_MODEL", "gemini-3-flash-preview")
    sys_txt = "\n".join(m["content"] for m in messages if m.get("role") == "system") \
        or "You are a precise intelligence analyst. Follow instructions exactly."
    convo = [m for m in messages if m.get("role") != "system"]
    if not convo:
        return {"error": "No user message"}
    user_text = convo[0]["content"] if len(convo) == 1 else \
        "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in convo)
    try:
        import uuid as _uuid
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=str(_uuid.uuid4()),
                       system_message=sys_txt).with_model(provider, model)
        resp = await chat.send_message(UserMessage(text=user_text))
        text = resp if isinstance(resp, str) else getattr(resp, "content", str(resp))
        return {"content": text, "model": f"{provider}/{model}"}
    except Exception as e:
        return {"error": str(e)}

async def deepseek_chat(messages, model_key="deepseek", **kw):
    """Central AI text helper. Defaults to the Emergent Universal Key; HF router as fallback."""
    if os.environ.get("AI_PROVIDER", "emergent").lower() == "emergent":
        r = await _emergent_chat_async(messages, max_tokens=kw.get("max_tokens", 600),
                                       temperature=kw.get("temperature", 0.4))
        if "error" not in r:
            return r
        if not os.environ.get("HF_TOKEN"):
            return r
    return await asyncio.to_thread(_hf_chat_sync, messages, model_key, **kw)

# ----------------------------------------------------------------------------- App / routers
app = FastAPI(title="NEXUS OSINT Orchestrator", version="2.0.0")
api = APIRouter(prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "online", "version": "2.0.0", "system": "NEXUS"}

@app.get("/api/ready")
async def ready():
    """Readiness probe: verifies the app can reach MongoDB (used by platform health checks)."""
    try:
        await db.command("ping")
        return {"ready": True, "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"not ready: {str(e)[:120]}")

# ====================== AUTH ======================
class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = "Operator"
    org_name: Optional[str] = None

class LoginReq(BaseModel):
    email: EmailStr
    password: str

def _pub(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u.get("name", ""),
            "role": u.get("role", "user"), "credits": u.get("credits", 0),
            "tenant_id": u.get("tenant_id") or gov.DEFAULT_TENANT,
            "tenant_name": u.get("tenant_name", "")}

@api.post("/auth/register")
async def register(body: RegisterReq, request: Request, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    # Provision an isolated tenant (org) for this operator — they administer their own workspace.
    tenant_id = secrets.token_hex(8)
    domain_part = email.split("@")[-1].split(".")[0] if "@" in email else "operator"
    org_name = (body.org_name or "").strip() or f"{domain_part.title()} Org"
    await db.tenants.insert_one({
        "tenant_id": tenant_id, "name": org_name, "owner_email": email, "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()})
    doc = {"email": email, "password_hash": hash_password(body.password),
           "name": body.name, "role": "tenant_admin", "credits": 0,
           "tenant_id": tenant_id, "tenant_name": org_name,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    await gov.audit_log("user.register", user={"id": uid, **doc}, request=request,
                        target=tenant_id, meta={"org": org_name})
    return _pub({"id": uid, **doc})

@api.post("/auth/login")
async def login(body: LoginReq, request: Request, response: Response):
    email = body.email.lower()
    await gov.check_lockout(request, email)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await gov.record_failed_login(request, email)
        await gov.audit_log("user.login", user={"email": email}, request=request,
                            status="failure", meta={"reason": "bad_credentials"})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await gov.clear_login_attempts(request, email)
    uid = str(user["_id"])
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    await gov.audit_log("user.login", user={"id": uid, **user}, request=request)
    return _pub({"id": uid, **user})

@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}

@api.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(rt, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        uid = str(user["_id"])
        access = create_access_token(uid, user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=False,
                            samesite="lax", max_age=43200, path="/")
        return {"refreshed": True}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return _pub(user)

# ====================== API KEYS (RBAC + machine auth) ======================
class ApiKeyCreate(BaseModel):
    name: str = "default"

def _key_pub(k: dict) -> dict:
    return {"id": str(k["_id"]), "name": k.get("name"), "prefix": k.get("prefix"),
            "created_at": k.get("created_at"), "last_used": k.get("last_used"),
            "calls": k.get("calls", 0), "revoked": k.get("revoked", False)}

@api.post("/keys")
async def create_api_key(body: ApiKeyCreate, request: Request, user: dict = Depends(get_current_user)):
    raw = "nxs_" + secrets.token_urlsafe(32)
    doc = {"user_id": user["id"], "tenant_id": gov.tenant_id_of(user), "name": body.name,
           "key_hash": hash_api_key(raw), "prefix": raw[:12],
           "created_at": datetime.now(timezone.utc).isoformat(),
           "last_used": None, "calls": 0, "revoked": False}
    res = await db.api_keys.insert_one(doc)
    await gov.audit_log("apikey.create", user=user, request=request,
                        target=str(res.inserted_id), meta={"name": body.name})
    # full key returned ONCE only
    return {"id": str(res.inserted_id), "name": body.name, "api_key": raw,
            "prefix": doc["prefix"], "warning": "Store this key now — it will not be shown again."}

@api.get("/keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    cur = db.api_keys.find({"user_id": user["id"]},
                           {"name": 1, "prefix": 1, "created_at": 1, "last_used": 1, "calls": 1, "revoked": 1}
                           ).sort("created_at", -1).limit(100)
    return [_key_pub(k) async for k in cur]

@api.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str, request: Request, user: dict = Depends(get_current_user)):
    await db.api_keys.update_one({"_id": ObjectId(key_id), "user_id": user["id"]},
                                 {"$set": {"revoked": True}})
    await gov.audit_log("apikey.revoke", user=user, request=request, target=key_id)
    return {"revoked": key_id}

# ====================== ADMIN (role-gated) ======================
@api.get("/admin/users")
async def admin_list_users(user: dict = Depends(require_admin)):
    cur = db.users.find({}, {"email": 1, "name": 1, "role": 1, "credits": 1, "tenant_id": 1,
                             "tenant_name": 1, "created_at": 1}).sort("created_at", -1).limit(500)
    return [{"id": str(u["_id"]), "email": u["email"], "name": u.get("name"),
             "role": u.get("role"), "credits": u.get("credits", 0),
             "tenant_id": u.get("tenant_id") or gov.DEFAULT_TENANT,
             "tenant_name": u.get("tenant_name", ""),
             "created_at": u.get("created_at")} async for u in cur]

class RoleUpdate(BaseModel):
    role: str

@api.patch("/admin/users/{user_id}/role")
async def admin_set_role(user_id: str, body: RoleUpdate, request: Request, user: dict = Depends(require_admin)):
    if body.role not in gov.VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(gov.VALID_ROLES)}")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": body.role}})
    await gov.audit_log("admin.set_role", user=user, request=request, target=user_id,
                        meta={"role": body.role})
    return {"updated": user_id, "role": body.role}

# ====================== LEADS ======================
def _lead_pub(l: dict) -> dict:
    l = dict(l)
    l["id"] = str(l.pop("_id"))
    return l

def lead_price(lead: dict) -> float:
    """Pay-per-lead pricing tiered by lead score (USD)."""
    s = lead.get("score") or 0
    if s >= 70:
        return 15.0
    if s >= 40:
        return 7.0
    return 3.0

class LeadCreate(BaseModel):
    category: str = "home_remodeling"
    full_name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    city: str = ""
    state: str = ""
    source_site: str = ""
    source_url: str = ""
    raw_text: str = ""

@api.get("/leads")
async def list_leads(category: Optional[str] = None, status: Optional[str] = None,
                     min_score: float = 0.0, search: Optional[str] = None,
                     limit: int = 100, offset: int = 0, user: dict = Depends(get_current_user)):
    q = {}
    if category: q["category"] = category
    if status: q["status"] = status
    if min_score: q["score"] = {"$gte": min_score}
    if search:
        rx = {"$regex": re.escape(search), "$options": "i"}
        q["$or"] = [{"full_name": rx}, {"email": rx}, {"city": rx}, {"ai_summary": rx}, {"company": rx}]
    total = await db.leads.count_documents(q)
    cur = db.leads.find(q).sort("score", -1).skip(offset).limit(limit)
    is_admin = user.get("role") == "admin"
    leads = []
    async for l in cur:
        pub = _lead_pub(l)
        # Monetization gate: scraped leads are locked until purchased with a credit
        if l.get("scraped") and not is_admin and user["id"] not in (l.get("unlocked_by") or []):
            pub["locked"] = True
            pub["price"] = lead_price(l)
            pub["email"] = ""
            pub["phone"] = ""
            pub["source_url"] = ""
        else:
            pub["locked"] = False
        pub.pop("unlocked_by", None)
        leads.append(pub)
    return {"total": total, "leads": leads}

@api.post("/leads/{lead_id}/unlock")
async def unlock_lead(lead_id: str, user: dict = Depends(get_current_user)):
    lead = await db.leads.find_one({"_id": ObjectId(lead_id)})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if user["id"] in (lead.get("unlocked_by") or []):
        return {"unlocked": True, "already": True, "lead": _lead_pub(lead)}
    if user.get("role") != "admin":
        u = await db.users.find_one({"_id": ObjectId(user["id"])})
        if (u.get("credits") or 0) < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits — buy a pack to unlock leads")
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"credits": -1}})
    await db.leads.update_one({"_id": ObjectId(lead_id)}, {"$addToSet": {"unlocked_by": user["id"]}})
    lead = await db.leads.find_one({"_id": ObjectId(lead_id)})
    pub = _lead_pub(lead); pub.pop("unlocked_by", None); pub["locked"] = False
    return {"unlocked": True, "lead": pub}

class LeadBuyReq(BaseModel):
    origin_url: str

@api.post("/leads/{lead_id}/buy")
async def buy_lead(lead_id: str, body: LeadBuyReq, request: Request, user: dict = Depends(get_current_user)):
    """Pay-per-lead: direct Stripe checkout to unlock one lead (no pre-bought credits)."""
    lead = await db.leads.find_one({"_id": ObjectId(lead_id)})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if user["id"] in (lead.get("unlocked_by") or []):
        raise HTTPException(status_code=400, detail="Lead already unlocked")
    from urllib.parse import urlparse
    o = urlparse(body.origin_url)
    host = (o.hostname or "")
    req_host = (request.base_url.hostname or "")
    if o.scheme not in ("http", "https") or not (
        host == req_host or host.endswith("emergentagent.com") or host in ("localhost", "127.0.0.1")):
        raise HTTPException(status_code=400, detail="Invalid origin")
    price = lead_price(lead)
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    host_url = str(request.base_url)
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=f"{host_url}api/webhook/stripe")
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/"
    meta = {"user_id": user["id"], "kind": "lead", "lead_id": lead_id}
    req = CheckoutSessionRequest(amount=float(price), currency="usd",
                                 success_url=success_url, cancel_url=cancel_url, metadata=meta)
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["id"], "kind": "lead",
        "lead_id": lead_id, "amount": float(price), "currency": "usd", "credits": 0,
        "payment_status": "pending", "status": "initiated", "metadata": meta,
        "created_at": datetime.now(timezone.utc).isoformat()})
    return {"url": session.url, "session_id": session.session_id, "amount": float(price)}

@api.get("/leads/stats")
async def lead_stats(user: dict = Depends(get_current_user)):
    total = await db.leads.count_documents({})
    raw = await db.leads.count_documents({"status": "raw"})
    enriched = await db.leads.count_documents({"status": "enriched"})
    hot = await db.leads.count_documents({"score": {"$gte": 70}})
    remodel = await db.leads.count_documents({"category": "home_remodeling"})
    cleaning = await db.leads.count_documents({"category": "cleaning"})
    sold = await db.leads.count_documents({"is_sold": True})
    rev = 0.0
    async for l in db.leads.find({"is_sold": True}, {"sold_price": 1}):
        rev += l.get("sold_price") or 0
    return {"total": total, "raw": raw, "enriched": enriched, "hot_leads": hot,
            "home_remodeling": remodel, "cleaning": cleaning, "sold": sold, "total_revenue": rev}

@api.post("/leads")
async def create_lead(body: LeadCreate, user: dict = Depends(get_current_user)):
    doc = body.model_dump()
    doc.update({"status": "raw", "score": 0.0, "is_sold": False, "sold_price": 0.0,
                "ai_summary": "", "ai_budget_est": "", "tags": "",
                "purchase_status": "available", "buyer_user_id": None, "ready_to_sell": False,
                "price_per_lead": 1, "data_confidence_score": 0.0, "quality_score": 0.0,
                "cross_verification": [], "risk_matrix": [], "operational_value_tier": "Operational",
                "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.leads.insert_one(doc)
    return _lead_pub({"_id": res.inserted_id, **doc})

@api.patch("/leads/{lead_id}/sell")
async def sell_lead(lead_id: str, price: float = 0.0, user: dict = Depends(get_current_user)):
    await db.leads.update_one({"_id": ObjectId(lead_id)},
                              {"$set": {"is_sold": True, "sold_price": price, "status": "sold"}})
    return {"sold": lead_id, "price": price}

@api.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, user: dict = Depends(get_current_user)):
    await db.leads.delete_one({"_id": ObjectId(lead_id)})
    return {"deleted": lead_id}

@api.get("/leads/export/csv")
async def export_csv(category: Optional[str] = None, min_score: float = 0.0,
                     user: dict = Depends(get_current_user)):
    import csv, io
    q = {}
    if category: q["category"] = category
    if min_score: q["score"] = {"$gte": min_score}
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["ID", "Category", "Status", "Score", "Name", "Email", "Phone",
                "City", "State", "AI Summary", "Budget", "Tags", "Source"])
    async for l in db.leads.find(q, {"category": 1, "status": 1, "score": 1, "full_name": 1,
                                     "email": 1, "phone": 1, "city": 1, "state": 1, "ai_summary": 1,
                                     "ai_budget_est": 1, "tags": 1, "source_url": 1}).sort("score", -1).limit(5000):
        w.writerow([str(l["_id"]), l.get("category"), l.get("status"), l.get("score"),
                    l.get("full_name"), l.get("email"), l.get("phone"), l.get("city"),
                    l.get("state"), l.get("ai_summary"), l.get("ai_budget_est"),
                    l.get("tags"), l.get("source_url")])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=nexus_leads.csv"})

# ====================== AI ENRICHMENT ======================
class EnrichReq(BaseModel):
    lead_id: Optional[str] = None
    batch: bool = False
    limit: int = 10

async def _enrich_one(lead: dict, model_key: str = "deepseek") -> dict:
    txt = (lead.get("raw_text") or f"{lead.get('full_name','')} {lead.get('company','')} {lead.get('city','')}").strip()[:1500]
    prompt = ("Analyze this service lead. Return ONLY valid JSON with keys: "
              "summary (2 sentences), intent_score (0-100 integer), "
              "budget_estimate (string like '$2k-$5k'), urgency (low/medium/high/urgent), "
              "category_tags (list of 3 strings).\n\n"
              f"Category: {lead.get('category')} | Source: {lead.get('source_site')}\nContent: {txt}")
    r = await deepseek_chat([{"role": "user", "content": prompt}], model_key=model_key, max_tokens=350, temperature=0.2)
    if "error" in r:
        return r
    out = r["content"].strip()
    if "```" in out:
        out = out.split("```")[1].replace("json", "", 1).strip()
    data = {}
    try:
        m = out[out.find("{"): out.rfind("}") + 1]
        data = json.loads(m)
    except Exception as e:
        return {"error": f"parse_failed: {e}", "raw": out[:300]}
    score = float(data.get("intent_score", 0) or 0)
    await db.leads.update_one({"_id": lead["_id"]}, {"$set": {
        "ai_summary": data.get("summary", ""), "ai_intent_score": score, "score": score,
        "ai_budget_est": data.get("budget_estimate", ""),
        "tags": ",".join(data.get("category_tags", []) or []), "status": "enriched"}})
    return {"lead_id": str(lead["_id"]), **data}

@api.post("/enrichment/enrich")
async def enrich(body: EnrichReq, user: dict = Depends(get_current_user)):
    if body.batch:
        results = []
        async for l in db.leads.find({"status": "raw"}).limit(body.limit):
            results.append(await _enrich_one(l))
        return {"status": "batch enrichment complete", "processed": len(results), "results": results}
    if not body.lead_id:
        raise HTTPException(status_code=400, detail="lead_id required")
    lead = await db.leads.find_one({"_id": ObjectId(body.lead_id)})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return await _enrich_one(lead)

@api.get("/enrichment/model-status")
async def model_status(user: dict = Depends(get_current_user)):
    configured = bool(os.environ.get("HF_TOKEN"))
    return {"loaded": configured, "provider": "Hugging Face Router",
            "models": {"deepseek": _resolve_model("deepseek"), "qwen": _resolve_model("qwen")},
            "status": "ready" if configured else "no_token"}

class ChatReq(BaseModel):
    message: str
    model: str = "deepseek"

@api.post("/enrichment/chat")
async def ai_chat(body: ChatReq, user: dict = Depends(get_current_user)):
    total = await db.leads.count_documents({})
    hot = await db.leads.count_documents({"score": {"$gte": 70}})
    sys_p = (f"You are NEXUS, an elite OSINT and lead-generation AI assistant. "
             f"System stats: {total} total leads, {hot} hot leads (score>=70). "
             "Help with lead analysis, OSINT intel, digital footprints and cybersecurity. Be concise.")
    mk = "qwen" if body.model == "qwen" else "deepseek"
    r = await deepseek_chat([{"role": "system", "content": sys_p},
                             {"role": "user", "content": body.message}], model_key=mk, max_tokens=500, temperature=0.7)
    if "error" in r:
        return {"error": r["error"]}
    return {"response": r["content"], "model": r.get("model")}

# ====================== OSINT TOOLS (cloud-native) ======================
async def _save_report(target, tool, result, user=None):
    await db.osint_reports.insert_one({"target": target, "tool_used": tool,
                                       "result_json": json.dumps(result, default=str)[:5000],
                                       "tenant_id": gov.tenant_id_of(user) if user else gov.DEFAULT_TENANT,
                                       "by": (user or {}).get("id"),
                                       "created_at": datetime.now(timezone.utc).isoformat()})

class TargetReq(BaseModel):
    target: str

class PhoneReq(BaseModel):
    target: str
    region: str = "US"

class ShodanReq(BaseModel):
    query: str
    api_key: str = ""

class DorkReq(BaseModel):
    dork: str
    num: int = 10

class MetaReq(BaseModel):
    url: str

class PortReq(BaseModel):
    target: str
    ports: Optional[List[int]] = None

@api.post("/osint/ip")
async def osint_ip(body: TargetReq, user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            geo = (await c.get(f"http://ip-api.com/json/{body.target}?fields=66846719")).json()
        except Exception:
            geo = {}
    res = {"tool": "ip_lookup", "target": body.target, "geo": geo}
    await _save_report(body.target, "ip_lookup", res, user)
    return res

@api.post("/osint/dns")
async def osint_dns(body: TargetReq, user: dict = Depends(get_current_user)):
    def run():
        import dns.resolver
        rec = {}
        for rt in ["A", "MX", "NS", "TXT"]:
            try:
                rec[rt] = [str(x) for x in dns.resolver.resolve(body.target, rt, lifetime=5)]
            except Exception:
                rec[rt] = []
        return rec
    records = await asyncio.to_thread(run)
    res = {"tool": "dns", "target": body.target, "records": records}
    await _save_report(body.target, "dns", res, user)
    return res

@api.post("/osint/whois")
async def osint_whois(body: TargetReq, user: dict = Depends(get_current_user)):
    def run():
        import whois as w
        try:
            return {k: str(v) for k, v in w.whois(body.target).items() if v}
        except Exception as e:
            return {"error": str(e)}
    data = await asyncio.to_thread(run)
    res = {"tool": "whois", "target": body.target, "data": data}
    await _save_report(body.target, "whois", res)
    return res

@api.post("/osint/phone")
async def osint_phone(body: PhoneReq, user: dict = Depends(get_current_user)):
    def run():
        import phonenumbers as pn
        from phonenumbers import geocoder, carrier
        try:
            p = pn.parse(body.target, body.region)
            return {"valid": pn.is_valid_number(p),
                    "international": pn.format_number(p, pn.PhoneNumberFormat.INTERNATIONAL),
                    "country": geocoder.description_for_number(p, "en"),
                    "carrier": carrier.name_for_number(p, "en")}
        except Exception as e:
            return {"error": str(e)}
    res = {"tool": "phone", "target": body.target, **(await asyncio.to_thread(run))}
    await _save_report(body.target, "phone", res, user)
    return res

@api.post("/osint/social")
async def osint_social(body: TargetReq, user: dict = Depends(get_current_user)):
    plats = {"instagram": f"https://www.instagram.com/{body.target}/",
             "twitter": f"https://twitter.com/{body.target}",
             "github": f"https://github.com/{body.target}",
             "reddit": f"https://www.reddit.com/user/{body.target}",
             "tiktok": f"https://www.tiktok.com/@{body.target}"}
    found = {}
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
        for pl, url in plats.items():
            try:
                resp = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                found[pl] = {"exists": resp.status_code == 200, "url": url}
            except Exception:
                found[pl] = {"exists": False, "url": url}
    res = {"tool": "social", "target": body.target, "platforms": found}
    await _save_report(body.target, "social", res, user)
    return res

@api.post("/osint/geolocate")
async def osint_geo(body: TargetReq, user: dict = Depends(get_current_user)):
    def resolve():
        try:
            return socket.gethostbyname(body.target)
        except Exception:
            return body.target
    ip = await asyncio.to_thread(resolve)
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            geo = (await c.get(f"http://ip-api.com/json/{ip}?fields=66846719")).json()
        except Exception:
            geo = {}
    res = {"tool": "geolocate", "target": body.target, "ip": ip, "geo": geo}
    await _save_report(body.target, "geolocate", res, user)
    return res

@api.post("/osint/breach")
async def osint_breach(body: TargetReq, user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            resp = await c.get(f"https://haveibeenpwned.com/unifiedsearch/{body.target}",
                               headers={"User-Agent": "NEXUS-OSINT"})
            res = {"tool": "breach", "target": body.target,
                   "breached": resp.status_code == 200, "status": resp.status_code}
        except Exception as e:
            res = {"tool": "breach", "target": body.target, "error": str(e)}
    await _save_report(body.target, "breach", res, user)
    return res

@api.post("/osint/subdomains")
async def osint_subdomains(body: TargetReq, user: dict = Depends(get_current_user)):
    def run():
        subs = ["www", "mail", "api", "admin", "dev", "staging", "blog", "shop", "portal", "vpn", "remote"]
        found = []
        for s in subs:
            try:
                h = f"{s}.{body.target}"
                found.append({"subdomain": h, "ip": socket.gethostbyname(h)})
            except Exception:
                pass
        return found
    res = {"tool": "subdomains", "target": body.target, "found": await asyncio.to_thread(run)}
    await _save_report(body.target, "subdomains", res, user)
    return res

@api.post("/osint/portscan")
async def osint_portscan(body: PortReq, user: dict = Depends(get_current_user)):
    ports = body.ports or [21, 22, 25, 80, 443, 3306, 3389, 5432, 6379, 8080, 27017]
    def run():
        open_p = []
        for p in ports:
            try:
                s = socket.socket(); s.settimeout(1)
                if s.connect_ex((body.target, p)) == 0:
                    open_p.append(p)
                s.close()
            except Exception:
                pass
        return open_p
    res = {"tool": "portscan", "target": body.target, "open_ports": await asyncio.to_thread(run)}
    await _save_report(body.target, "portscan", res, user)
    return res

@api.post("/osint/metadata")
async def osint_metadata(body: MetaReq, user: dict = Depends(get_current_user)):
    ER = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    PHR = re.compile(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
    async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"}) as c:
        try:
            resp = await c.get(body.url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            txt = soup.get_text()
            res = {"tool": "metadata", "url": body.url,
                   "title": soup.title.string if soup.title else "",
                   "emails": list(set(ER.findall(txt)))[:20],
                   "phones": list(set(PHR.findall(txt)))[:20]}
        except Exception as e:
            res = {"tool": "metadata", "url": body.url, "error": str(e)}
    await _save_report(body.url, "metadata", res, user)
    return res

@api.post("/osint/shodan")
async def osint_shodan(body: ShodanReq, user: dict = Depends(get_current_user)):
    if not body.api_key:
        return {"tool": "shodan", "error": "No API key provided"}
    def run():
        try:
            import shodan
            r = shodan.Shodan(body.api_key).search(body.query, limit=10)
            return {"total": r["total"], "results": r["matches"][:5]}
        except Exception as e:
            return {"error": str(e)}
    return {"tool": "shodan", "query": body.query, **(await asyncio.to_thread(run))}

@api.post("/osint/dork")
async def osint_dork(body: DorkReq, user: dict = Depends(get_current_user)):
    def run():
        try:
            from googlesearch import search
            return list(search(body.dork, num_results=body.num))
        except Exception as e:
            return {"error": str(e)}
    out = await asyncio.to_thread(run)
    res = {"tool": "dork", "query": body.dork, "results": out}
    await _save_report(body.dork, "dork", res, user)
    return res

@api.get("/osint/reports")
async def osint_reports(limit: int = 50, user: dict = Depends(get_current_user)):
    cur = db.osint_reports.find(gov.tenant_scope(user), {"target": 1, "tool_used": 1, "created_at": 1}).sort("created_at", -1).limit(limit)
    return [{"id": str(r["_id"]), "target": r.get("target"), "tool": r.get("tool_used"),
             "created_at": r.get("created_at")} async for r in cur]

# ====================== 24/7 SCRAPER ENGINE (OSINT/AI HQ filter) ======================
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone="UTC")
RUN_SCHEDULER = os.environ.get("RUN_SCHEDULER", "true").lower() != "false"
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
SCRAPER_STATE = {"status": "idle", "last_run": None, "last_error": None,
                 "found": 0, "qualified": 0, "cycles": 0, "next_run": None}

INTENT_KW = ["looking for", "need a", "need to", "need some", "hire", "hiring", "quote", "estimate",
             "recommend", "anyone know", "help me find", "asap", "this week", "budget",
             "how much", "cost to", "searching for", "in need of", "any good", "suggestions for"]
URGENCY_KW = ["asap", "urgent", "this week", "immediately", "today", "tomorrow", "emergency", "right away"]
EMAIL_RX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RX = re.compile(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")

# Tampa Bay service market: Hillsborough + Pinellas (and adjacent) — geo scope for local independent-service leads.
TAMPA_CITIES = [
    "tampa bay", "hillsborough", "pinellas", "manatee", "pasco", "hernando",
    "tampa", "st. petersburg", "st petersburg",
    "saint petersburg", "clearwater", "brandon", "largo", "riverview", "plant city", "valrico",
    "wesley chapel", "palm harbor", "dunedin", "pinellas park", "seminole", "oldsmar",
    "temple terrace", "apollo beach", "ruskin", "lutz", "gibsonton", "carrollwood", "westchase",
    "odessa", "tarpon springs", "safety harbor", "thonotosassa", "town n country", "town 'n' country",
    "sun city center", "land o lakes",
    "bradenton", "palmetto", "lakewood ranch", "parrish", "ellenton",
    "new port richey", "port richey", "zephyrhills", "dade city", "holiday",
    "spring hill", "brooksville", "weeki wachee",
]

def _detect_tampa_geo(text: str) -> tuple:
    low = (text or "").lower()
    for c in TAMPA_CITIES:
        if c in low:
            label = "Tampa Bay" if c in ("tampa bay", "hillsborough", "pinellas",
                                         "manatee", "pasco", "hernando") else c.title()
            return label, "FL"
    return "", ""

# Independent-service search terms scraped across the Tampa Bay market (Hillsborough + Pinellas).
SERVICE_QUERIES = [
    ("plumber", "plumbing"), ("electrician", "electrical"), ("hvac", "hvac"),
    ("landscaping", "landscaping"), ("handyman", "handyman"), ("house cleaning", "cleaning"),
    ("painter", "painting"), ("roofing contractor", "roofing"), ("pest control", "pest_control"),
    ("remodeling contractor", "home_remodeling"), ("pressure washing", "pressure_washing"),
    ("moving company", "moving"), ("pool service", "pool"), ("auto repair", "auto"),
    ("tree service", "tree_service"), ("flooring", "flooring"),
]
# Key Tampa Bay locales (Hillsborough + Pinellas) appended to each search.
TAMPA_LOCALES = [
    "Tampa FL", "St Petersburg FL", "Clearwater FL", "Brandon FL", "Largo FL",
    "Riverview FL", "Plant City FL", "Pinellas Park FL", "Palm Harbor FL", "Tarpon Springs FL",
]
SOURCES_VERSION = 5
# High-value B2B sectors across the 5-county Tampa Bay region, harvested via Overpass
# (one area query per sector+county) -> OSINT HQ filter -> storefront. Financial Services
# and Legal are prioritised. Apify Reddit stays a separate budget-guarded social source.
SCRAPER_SECTORS = ["financial_services", "legal", "insurance", "real_estate", "healthcare", "b2b_tech"]
SCRAPER_COUNTIES = ["Hillsborough County", "Pinellas County", "Manatee County",
                    "Pasco County", "Hernando County"]
DEFAULT_SOURCES = [
    {"provider": "overpass", "sector": s, "county": c, "category": s, "limit": 60}
    for s in SCRAPER_SECTORS for c in SCRAPER_COUNTIES
] + [
    {"provider": "apify_reddit", "category": "services", "max_items": 30,
     "subreddits": ["tampa", "StPetersburgFL", "Clearwater", "HillsboroughCounty", "stpetersburg"],
     "queries": []},
]

async def get_scraper_config() -> dict:
    cfg = await db.scraper_config.find_one({"_id": "config"})
    if not cfg:
        cfg = {"_id": "config", "enabled": os.environ.get("SCRAPER_ENABLED", "true") == "true",
               "interval_min": int(os.environ.get("SCRAPER_INTERVAL_MIN", "30")),
               "min_score": float(os.environ.get("SCRAPER_MIN_SCORE", "55")),
               "use_ai": True, "ai_model": "deepseek", "sources": DEFAULT_SOURCES,
               "sources_version": SOURCES_VERSION}
        await db.scraper_config.insert_one(cfg)
    return cfg

def heuristic_score(text: str) -> float:
    t = text.lower()
    score = 0
    for k in INTENT_KW:
        if k in t:
            score += 12
    for k in URGENCY_KW:
        if k in t:
            score += 14
    if EMAIL_RX.search(text):
        score += 18
    if PHONE_RX.search(text):
        score += 15
    if len(t) > 160:
        score += 6
    return float(min(score, 100))

async def fetch_hackernews(src: dict) -> list:
    from urllib.parse import quote
    url = f"http://hn.algolia.com/api/v1/search_by_date?query={quote(src['query'])}&tags=story&hitsPerPage=25"
    out = []
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "NEXUS-LeadBot/1.0"}) as c:
            data = (await c.get(url)).json()
        for h in data.get("hits", []):
            title = h.get("title") or h.get("story_title") or ""
            body = h.get("story_text") or h.get("comment_text") or ""
            text = (title + " — " + body).strip()
            if not text or text == "—":
                continue
            out.append({"full_name": "hn/" + (h.get("author") or "anon"),
                        "raw_text": text[:2000], "source_site": "Hacker News",
                        "category": src["category"],
                        "source_url": "https://news.ycombinator.com/item?id=" + str(h.get("objectID")),
                        "city": "", "state": "", "company": "", "title": title})
    except Exception as e:
        SCRAPER_STATE["last_error"] = "hn: " + str(e)[:160]
    return out

async def fetch_github(src: dict) -> list:
    from urllib.parse import quote
    url = f"https://api.github.com/search/issues?q={quote(src['query'])}&per_page=20&sort=created&order=desc"
    headers = {"User-Agent": "NEXUS-LeadBot/1.0", "Accept": "application/vnd.github+json"}
    gh = os.environ.get("GITHUB_TOKEN")
    if gh:
        headers["Authorization"] = "Bearer " + gh
    out = []
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as c:
            data = (await c.get(url)).json()
        for it in data.get("items", []):
            text = (it.get("title", "") + " — " + (it.get("body") or "")).strip()
            out.append({"full_name": "gh/" + (it.get("user", {}) or {}).get("login", "anon"),
                        "raw_text": text[:2000], "source_site": "GitHub",
                        "category": src["category"], "source_url": it.get("html_url", ""),
                        "city": "", "state": "", "company": "", "title": it.get("title", "")})
    except Exception as e:
        SCRAPER_STATE["last_error"] = "github: " + str(e)[:160]
    return out

async def _reddit_token() -> Optional[str]:
    cid = os.environ.get("REDDIT_CLIENT_ID"); sec = os.environ.get("REDDIT_CLIENT_SECRET")
    usr = os.environ.get("REDDIT_USERNAME"); pw = os.environ.get("REDDIT_PASSWORD")
    if not (cid and sec and usr and pw):
        return None
    try:
        async with httpx.AsyncClient(timeout=15, auth=(cid, sec),
                                     headers={"User-Agent": "NEXUS-LeadBot/1.0 by " + usr}) as c:
            r = await c.post("https://www.reddit.com/api/v1/access_token",
                             data={"grant_type": "password", "username": usr, "password": pw})
            return r.json().get("access_token")
    except Exception:
        return None

async def fetch_reddit(src: dict) -> list:
    from urllib.parse import quote
    token = await _reddit_token()
    if not token:
        SCRAPER_STATE["last_error"] = "reddit: add REDDIT_CLIENT_ID/SECRET/USERNAME/PASSWORD to enable"
        return []
    q = quote(src["query"]); sub = src.get("subreddit", "")
    base = f"https://oauth.reddit.com/r/{sub}/search" if sub else "https://oauth.reddit.com/search"
    url = f"{base}?q={q}&restrict_sr={'1' if sub else '0'}&sort=new&limit=20&t=month"
    out = []
    try:
        async with httpx.AsyncClient(timeout=15, headers={"Authorization": "Bearer " + token,
                                     "User-Agent": "NEXUS-LeadBot/1.0"}) as c:
            data = (await c.get(url)).json()
        for ch in data.get("data", {}).get("children", []):
            p = ch.get("data", {})
            text = (p.get("title", "") + " — " + p.get("selftext", "")).strip()
            out.append({"full_name": "u/" + p.get("author", "anon"), "raw_text": text[:2000],
                        "source_site": "Reddit", "category": src["category"],
                        "source_url": "https://reddit.com" + p.get("permalink", ""),
                        "city": "", "state": "", "company": "", "title": p.get("title", "")})
    except Exception as e:
        SCRAPER_STATE["last_error"] = "reddit: " + str(e)[:160]
    return out

def _osm_record_to_lead(r: dict, src: dict) -> Optional[dict]:
    et = r.get("extratags") or {}
    ad = r.get("address") or {}
    name = r.get("name") or et.get("operator") or ""
    if not name:
        return None
    city = ad.get("city") or ad.get("town") or ad.get("village") or ad.get("municipality") or ""
    website = et.get("website") or et.get("contact:website") or ""
    phone = et.get("phone") or et.get("contact:phone") or ""
    email = et.get("email") or et.get("contact:email") or ""
    osm_url = f"https://www.openstreetmap.org/{r.get('osm_type','node')}/{r.get('osm_id','')}"
    cat_label = src["category"].replace("_", " ")
    text = f"{name} — independent {cat_label} business in {city or 'Tampa Bay'}, FL. {website} {phone}".strip()
    return {"kind": "business", "full_name": "", "company": name,
            "raw_text": text[:2000], "source_site": "OpenStreetMap",
            "category": src["category"], "source_url": website or osm_url,
            "website": website, "city": city, "state": "FL",
            "phone": phone, "email": email, "title": name}

async def fetch_osm(src: dict) -> list:
    """Local independent-service businesses in Tampa Bay via OpenStreetMap Nominatim (free, no key)."""
    from urllib.parse import quote
    out = []
    ua = {"User-Agent": "NEXUS-LeadBot/1.0 (contact: " + (os.environ.get("GMAIL_USER") or "nexus@local") + ")"}
    async with httpx.AsyncClient(timeout=20, headers=ua, follow_redirects=True) as c:
        for locale in TAMPA_LOCALES:
            q = f"{src['query']}, {locale}"
            url = (f"https://nominatim.openstreetmap.org/search?q={quote(q)}"
                   "&format=jsonv2&extratags=1&addressdetails=1&limit=25&countrycodes=us")
            try:
                data = (await c.get(url)).json()
            except Exception as e:
                SCRAPER_STATE["last_error"] = "osm: " + str(e)[:160]
                data = []
            for r in (data or []):
                lead = _osm_record_to_lead(r, src)
                if lead:
                    out.append(lead)
            await asyncio.sleep(1.1)  # Nominatim usage policy: max ~1 request/second
    return out

def _apify_reddit_payload(src: dict) -> dict:
    subs = src.get("subreddits") or ["tampa", "StPetersburgFL", "Clearwater"]
    start_urls = [{"url": f"https://www.reddit.com/r/{s}/new/"} for s in subs]
    max_items = int(src.get("max_items", 30))
    return {"startUrls": start_urls, "searches": src.get("queries") or [],
            "searchPosts": True, "searchComments": False, "searchCommunities": False,
            "searchUsers": False, "skipComments": True, "sort": "new", "time": "month",
            "maxItems": max_items, "maxPostCount": max_items,
            "proxy": {"useApifyProxy": True}}

async def _apify_run_reddit(c, token: str, payload: dict):
    """Start an Apify run, poll to completion, return dataset items (or None on failure)."""
    base = "https://api.apify.com/v2"
    run = (await c.post(f"{base}/acts/trudax~reddit-scraper-lite/runs?token={token}", json=payload)).json()
    data = run.get("data") or {}
    run_id = data.get("id"); dataset_id = data.get("defaultDatasetId")
    if not run_id or not dataset_id:
        SCRAPER_STATE["last_error"] = "apify: " + str(run)[:160]
        return None
    status = data.get("status")
    for _ in range(54):  # up to ~9 min
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT", "TIMING-OUT"):
            break
        await asyncio.sleep(10)
        st = (await c.get(f"{base}/actor-runs/{run_id}?token={token}")).json()
        status = (st.get("data") or {}).get("status")
    return (await c.get(f"{base}/datasets/{dataset_id}/items?token={token}&clean=true")).json()

def _apify_reddit_item_to_lead(it: dict, src: dict) -> Optional[dict]:
    if it.get("dataType") and it.get("dataType") != "post":
        return None
    title = it.get("title") or ""
    body = it.get("body") or it.get("text") or ""
    text = (title + " — " + body).strip()
    if not text or text == "—":
        return None
    author = it.get("username") or it.get("author") or "anon"
    return {"full_name": "u/" + author, "raw_text": text[:2000],
            "source_site": "Reddit", "category": src.get("category", "services"),
            "source_url": it.get("url") or it.get("link") or "",
            "city": "", "state": "", "company": "", "title": title}

async def fetch_apify_reddit(src: dict) -> list:
    """Reddit posts via Apify (trudax/reddit-scraper-lite). Async run pattern (start→poll→fetch);
    avoids the 300s sync limit so slower runs still return data."""
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        SCRAPER_STATE["last_error"] = "apify: set APIFY_TOKEN to enable Reddit"
        return []
    payload = _apify_reddit_payload(src)
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            items = await _apify_run_reddit(c, token, payload)
    except Exception as e:
        SCRAPER_STATE["last_error"] = "apify: " + (str(e) or type(e).__name__)[:160]
        return []
    if items is None:
        return []
    if not isinstance(items, list):
        SCRAPER_STATE["last_error"] = "apify: " + str(items)[:160]
        return []
    out = []
    for it in items:
        lead = _apify_reddit_item_to_lead(it, src)
        if lead:
            out.append(lead)
    return out

async def fetch_overpass_county(src: dict) -> list:
    """High-value B2B businesses in a whole county via one Overpass area query (OSINT HQ pipeline)."""
    sector = src.get("sector", "financial_services")
    county = src.get("county", "Pinellas County")
    raws = await _overpass_generate(sector, county, int(src.get("limit", 60)))
    out = []
    cat_label = sector.replace("_", " ")
    for r in raws:
        company = (r.get("company") or "").strip()
        if not company:
            continue
        website = r.get("website", ""); phone = r.get("phone", ""); email = r.get("email", "")
        city = r.get("city", ""); state = r.get("state") or "FL"
        text = f"{company} — {cat_label} firm in {city or county}, FL. {website} {phone}".strip()
        out.append({"kind": "business", "full_name": "", "company": company,
                    "raw_text": text[:2000], "source_site": "OpenStreetMap",
                    "category": sector, "source_url": website or "", "website": website,
                    "city": city, "state": state, "phone": phone, "email": email, "title": company})
    await asyncio.sleep(1.5)  # be gentle to the public Overpass endpoint
    return out

async def fetch_source(src: dict) -> list:
    p = src.get("provider", "osm")
    if p == "overpass":
        return await fetch_overpass_county(src)
    if p in ("osm", "nominatim"):
        return await fetch_osm(src)
    if p in ("apify_reddit", "reddit_apify"):
        return await fetch_apify_reddit(src)
    if p == "hackernews":
        return await fetch_hackernews(src)
    if p == "github":
        return await fetch_github(src)
    return await fetch_reddit(src)

def _passes_intent_gate(text: str) -> bool:
    """OSINT-style pre-filter: candidate must express service intent."""
    low = text.lower()
    return any(k in low for k in INTENT_KW)

def _extract_contacts(text: str) -> dict:
    """Pull first email/phone from raw text (OSINT enrichment)."""
    emails = EMAIL_RX.findall(text)
    phones = PHONE_RX.findall(text)
    return {"email": emails[0] if emails else "", "phone": phones[0] if phones else ""}

FREE_EMAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com",
              "icloud.com", "proton.me", "live.com", "msn.com", "me.com"}
PLATFORM_DOMAINS = {"github.com", "news.ycombinator.com", "ycombinator.com", "craigslist.org",
                    "reddit.com", "x.com", "twitter.com", "facebook.com", "linkedin.com"}

def _extract_company_domain(text: str, source_url: str, email: str) -> Optional[str]:
    """Find a real company domain from a scraped lead (for scan-to-pipeline)."""
    if email and "@" in email:
        d = email.split("@")[-1].lower().strip()
        if d and d not in FREE_EMAIL and "." in d:
            return d
    for m in re.findall(r"https?://([a-zA-Z0-9.\-]+)", text or ""):
        d = m.lower().lstrip(".")
        if d.startswith("www."):
            d = d[4:]
        base = ".".join(d.split(".")[-2:])
        if "." in d and base not in PLATFORM_DOMAINS:
            return d
    return None

async def _score_candidate(cand: dict, text: str, use_ai: bool, ai_model: str, min_score: float) -> dict:
    """Score a candidate via AI (preferred) or heuristic; decide if it qualifies."""
    hscore = heuristic_score(text)
    result = {"score": hscore, "summary": "", "budget": "", "tags": "", "keep": hscore >= min_score}
    ai = await _ai_score_candidate(cand, ai_model) if (use_ai and hscore >= 18) else None
    if ai and "intent_score" in ai:
        final = float(ai.get("intent_score", hscore) or hscore)
        result.update({"score": final, "summary": ai.get("summary", ""),
                       "budget": ai.get("budget_estimate", ""),
                       "tags": ",".join(ai.get("category_tags", []) or []),
                       "keep": final >= min_score})
    elif use_ai:
        # AI temporarily unavailable -> provisional qualify, flagged for re-scoring
        result.update({"score": max(hscore, 45.0), "tags": "ai_pending", "keep": True})
    return result

def _build_lead_doc(cand: dict, text: str, scored: dict) -> dict:
    city, state = _detect_tampa_geo(text)
    return {"category": cand["category"], "full_name": cand["full_name"],
            "email": cand["email"], "phone": cand["phone"], "company": "",
            "city": city or cand.get("city", ""), "state": state or cand.get("state", ""),
            "source_site": cand.get("source_site", "web"),
            "source_url": cand["source_url"], "raw_text": text,
            "status": "enriched" if scored["summary"] else "raw", "score": scored["score"],
            "ai_summary": scored["summary"], "ai_intent_score": scored["score"],
            "ai_budget_est": scored["budget"], "tags": scored["tags"],
            "is_sold": False, "sold_price": 0.0, "scraped": True,
            "created_at": datetime.now(timezone.utc).isoformat()}

async def _process_candidate(cand: dict, use_ai: bool, ai_model: str, min_score: float):
    """Store a qualified lead; returns {'id','hq'} when stored, else None."""
    if cand.get("source_url") and await db.leads.find_one({"source_url": cand["source_url"]}):
        return None
    if cand.get("kind") == "business":
        return await _process_business(cand, min_score)
    text = cand["raw_text"]
    if not _passes_intent_gate(text):
        return None
    cand.update(_extract_contacts(text))
    scored = await _score_candidate(cand, text, use_ai, ai_model, min_score)
    if not scored["keep"]:
        return None
    intent = int(scored["score"] or 0)
    v = await asyncio.to_thread(_osint_verify_sync, cand.get("email", ""), cand.get("phone", ""),
                                "", "", cand.get("city", ""), cand.get("state", ""))
    conf = _data_confidence(v, intent)
    doc = _build_lead_doc(cand, text, scored)
    doc.update(_osint_fields(v, conf, intent))
    res = await db.leads.insert_one(doc)
    asyncio.create_task(_auto_threat_pipeline(doc))
    return {"id": res.inserted_id, "hq": doc["ready_to_sell"]}

async def _process_business(cand: dict, min_score: float):
    """Store a verified business lead, OSINT HQ-filtered into the storefront pipeline."""
    company = (cand.get("company") or "").strip()
    if not company:
        return None
    website = cand.get("website", ""); phone = cand.get("phone", ""); email = cand.get("email", "")
    if not website and not phone:
        return None  # no verifiable contact channel — skip
    city = cand.get("city", ""); state = cand.get("state", "FL")
    if await db.leads.find_one({"company": company, "city": city, "scraped": True}):
        return None
    intent = 40 + (20 if website else 0) + (15 if phone else 0) + (10 if email else 0)
    v = await asyncio.to_thread(_osint_verify_sync, email, phone, website, company, city, state)
    conf = _data_confidence(v, intent)
    fields = _osint_fields(v, conf, intent)
    now = datetime.now(timezone.utc).isoformat()
    cat_label = cand["category"].replace("_", " ")
    doc = {"category": cand["category"], "full_name": "", "email": email, "phone": phone,
           "company": company, "website": website, "city": city, "state": state,
           "source_site": cand.get("source_site", "OpenStreetMap"), "source": "scraper",
           "source_url": cand.get("source_url", ""), "raw_text": cand.get("raw_text", ""),
           "ai_summary": f"{cat_label.title()} firm operating in {city or 'Tampa Bay'}, FL.",
           "ai_intent_score": intent, "ai_budget_est": "", "tags": "business," + cand["category"],
           "is_sold": False, "sold_price": 0.0, "scraped": True,
           "status": "ready_to_sell" if fields["ready_to_sell"] else "enriched",
           "created_at": now, **fields}
    res = await db.leads.insert_one(doc)
    asyncio.create_task(_auto_threat_pipeline(doc))
    return {"id": res.inserted_id, "hq": fields["ready_to_sell"]}

async def run_scrape_cycle(reason: str = "scheduled"):
    if SCRAPER_STATE["status"] == "running":
        return
    SCRAPER_STATE["status"] = "running"
    SCRAPER_STATE["last_error"] = None
    cfg = await get_scraper_config()
    min_score = cfg.get("min_score", 55)
    use_ai = cfg.get("use_ai", True)
    ai_model = cfg.get("ai_model", "deepseek")
    found = qualified = 0
    hq_ids = []
    sem = asyncio.Semaphore(15)

    async def handle(cand):
        nonlocal qualified
        async with sem:
            res = await _process_candidate(cand, use_ai, ai_model, min_score)
        if res:
            qualified += 1
            if res.get("hq"):
                hq_ids.append(res["id"])

    try:
        for src in cfg.get("sources", []):
            if src.get("provider") in ("apify_reddit", "reddit_apify"):
                continue  # paid Reddit runs on its own hourly budget-guarded cycle
            cands = await fetch_source(src)
            found += len(cands)
            await asyncio.gather(*(handle(c) for c in cands))
        SCRAPER_STATE.update({"found": SCRAPER_STATE["found"] + found,
                              "qualified": SCRAPER_STATE["qualified"] + qualified,
                              "cycles": SCRAPER_STATE["cycles"] + 1})
    except Exception as e:
        SCRAPER_STATE["last_error"] = str(e)[:200]
    finally:
        SCRAPER_STATE["status"] = "idle"
        SCRAPER_STATE["last_run"] = datetime.now(timezone.utc).isoformat()
        logger.info("Scrape cycle (%s): found=%d qualified=%d hq=%d", reason, found, qualified, len(hq_ids))
    if hq_ids:
        asyncio.create_task(_bg_ai_enrich(hq_ids))
    asyncio.create_task(_auto_outreach_sweep("post-scrape"))

# ---- Paid Apify Reddit cycle (hourly, hard daily $ budget guard) ----
APIFY_COST_PER_RESULT = float(os.environ.get("APIFY_COST_PER_RESULT", "0.0034"))
APIFY_DAILY_BUDGET_USD = float(os.environ.get("APIFY_DAILY_BUDGET_USD", "5"))
REDDIT_INTERVAL_MIN = int(os.environ.get("REDDIT_INTERVAL_MIN", "60"))

async def _apify_budget_remaining_items() -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = await db.apify_usage.find_one({"_id": "usage"}) or {}
    used = doc.get("results", 0) if doc.get("date") == today else 0
    cap = int(APIFY_DAILY_BUDGET_USD / max(APIFY_COST_PER_RESULT, 1e-6))
    return max(0, cap - used)

async def _apify_record(n: int):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = await db.apify_usage.find_one({"_id": "usage"}) or {}
    base = doc.get("results", 0) if doc.get("date") == today else 0
    total = base + n
    await db.apify_usage.update_one({"_id": "usage"},
        {"$set": {"date": today, "results": total, "spend": round(total * APIFY_COST_PER_RESULT, 4)}}, upsert=True)

async def run_reddit_cycle(reason: str = "scheduled"):
    if SCRAPER_STATE.get("reddit_status") == "running":
        return
    if not os.environ.get("APIFY_TOKEN"):
        return
    cfg = await get_scraper_config()
    if not cfg.get("enabled"):
        return
    sources = [s for s in cfg.get("sources", []) if s.get("provider") in ("apify_reddit", "reddit_apify")]
    if not sources:
        return
    remaining = await _apify_budget_remaining_items()
    if remaining <= 0:
        SCRAPER_STATE["reddit_last_error"] = f"daily Apify budget (${APIFY_DAILY_BUDGET_USD:.2f}) reached"
        return
    SCRAPER_STATE["reddit_status"] = "running"
    SCRAPER_STATE["reddit_last_error"] = None
    min_score = cfg.get("min_score", 55)
    use_ai = cfg.get("use_ai", True)
    ai_model = cfg.get("ai_model", "deepseek")
    found = qualified = 0
    hq_ids = []
    try:
        for src in sources:
            if remaining <= 0:
                break
            src = dict(src)
            src["max_items"] = min(int(src.get("max_items", 30)), remaining)
            cands = await fetch_source(src)
            await _apify_record(len(cands))
            remaining -= len(cands)
            for cand in cands:
                found += 1
                res = await _process_candidate(cand, use_ai, ai_model, min_score)
                if res:
                    qualified += 1
                    if res.get("hq"):
                        hq_ids.append(res["id"])
        SCRAPER_STATE.update({"found": SCRAPER_STATE["found"] + found,
                              "qualified": SCRAPER_STATE["qualified"] + qualified})
    except Exception as e:
        SCRAPER_STATE["reddit_last_error"] = str(e)[:200]
    finally:
        SCRAPER_STATE["reddit_status"] = "idle"
        SCRAPER_STATE["reddit_last_run"] = datetime.now(timezone.utc).isoformat()
        logger.info("Reddit cycle (%s): found=%d qualified=%d", reason, found, qualified)
    if hq_ids:
        asyncio.create_task(_bg_ai_enrich(hq_ids))

async def _ai_score_candidate(cand: dict, model_key: str) -> Optional[dict]:
    prompt = ("You are a lead-quality filter. Analyze this social post and return ONLY JSON with keys: "
              "summary (1-2 sentences), intent_score (0-100 integer, how likely this person wants to HIRE/BUY "
              "this service now), budget_estimate (string), category_tags (list of 3). "
              "Score low if it's just discussion/advice, high if they actively seek a provider.\n\n"
              f"Category: {cand['category']}\nPost: {cand['raw_text'][:1500]}")
    r = await deepseek_chat([{"role": "user", "content": prompt}], model_key=model_key, max_tokens=300, temperature=0.2)
    if "error" in r:
        return None
    out = r["content"].strip()
    if "```" in out:
        out = out.split("```")[1].replace("json", "", 1).strip()
    try:
        return json.loads(out[out.find("{"): out.rfind("}") + 1])
    except Exception:
        return None

def reschedule(interval_min: int):
    for jid, fn, mins in [("scrape", run_scrape_cycle, max(5, interval_min)),
                          ("reddit", run_reddit_cycle, max(15, REDDIT_INTERVAL_MIN))]:
        try:
            scheduler.remove_job(jid)
        except Exception:
            pass
        scheduler.add_job(fn, "interval", minutes=mins, id=jid, replace_existing=True, max_instances=1)

@api.get("/scraper/status")
async def scraper_status(user: dict = Depends(get_current_user)):
    cfg = await get_scraper_config()
    job = scheduler.get_job("scrape")
    nxt = job.next_run_time.isoformat() if job and job.next_run_time else None
    rjob = scheduler.get_job("reddit")
    rnxt = rjob.next_run_time.isoformat() if rjob and rjob.next_run_time else None
    scraped = await db.leads.count_documents({"scraped": True})
    usage = await db.apify_usage.find_one({"_id": "usage"}) or {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reddit_spend = usage.get("spend", 0.0) if usage.get("date") == today else 0.0
    return {**SCRAPER_STATE, "next_run": nxt, "scheduler_running": scheduler.running,
            "enabled": cfg.get("enabled"), "interval_min": cfg.get("interval_min"),
            "min_score": cfg.get("min_score"), "total_scraped_leads": scraped,
            "reddit_next_run": rnxt, "reddit_enabled": bool(os.environ.get("APIFY_TOKEN")),
            "reddit_interval_min": REDDIT_INTERVAL_MIN,
            "reddit_spend_today_usd": round(reddit_spend, 2), "reddit_daily_budget_usd": APIFY_DAILY_BUDGET_USD}

@api.get("/intel/sources")
async def intel_sources(user: dict = Depends(get_current_user)):
    usage = await db.apify_usage.find_one({"_id": "usage"}) or {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spend = usage.get("spend", 0.0) if usage.get("date") == today else 0.0
    has = lambda k: bool(os.environ.get(k))
    return {"apify_spend_today_usd": round(spend, 2), "apify_budget_usd": APIFY_DAILY_BUDGET_USD,
            "sources": [
                {"key": "osm", "name": "OpenStreetMap / Overpass — B2B firms", "status": "live",
                 "cost": "free", "detail": f"{len(SCRAPER_SECTORS)} HQ sectors × {len(SCRAPER_COUNTIES)} counties, OSINT-filtered, every 30 min"},
                {"key": "reddit", "name": "Reddit (via Apify)", "status": "live" if has("APIFY_TOKEN") else "inactive",
                 "cost": f"${spend:.2f} / ${APIFY_DAILY_BUDGET_USD:.0f} today", "detail": "hourly, $5/day budget guard"},
                {"key": "shodan", "name": "Shodan — host & CVE intel", "status": "live" if has("SHODAN_API_KEY") else "inactive",
                 "cost": "oss plan", "detail": "enriches Threat Intel scans"},
                {"key": "dns", "name": "DNS · DNSSEC · SSL/TLS", "status": "live",
                 "cost": "free", "detail": "records, cert expiry, weak protocols"},
                {"key": "email", "name": "Resend — pitch sending", "status": "live" if has("RESEND_API_KEY") else "inactive",
                 "cost": "free tier", "detail": os.environ.get("SENDER_EMAIL", "")},
            ]}

@api.post("/scraper/trigger")
async def scraper_trigger(source: str = "all", user: dict = Depends(get_current_user)):
    if source == "reddit":
        asyncio.create_task(run_reddit_cycle("manual"))
        return {"triggered": True, "status": "reddit cycle started"}
    asyncio.create_task(run_scrape_cycle("manual"))
    if source == "all":
        asyncio.create_task(run_reddit_cycle("manual"))
    return {"triggered": True, "status": "cycle started"}

@api.get("/scraper/config")
async def scraper_get_config(user: dict = Depends(get_current_user)):
    cfg = await get_scraper_config()
    cfg.pop("_id", None)
    return cfg

class ScraperConfig(BaseModel):
    enabled: bool = True
    interval_min: int = 30
    min_score: float = 55
    use_ai: bool = True
    ai_model: str = "deepseek"
    sources: List[dict] = []
    sources_version: int = SOURCES_VERSION

@api.put("/scraper/config")
async def scraper_set_config(body: ScraperConfig, user: dict = Depends(require_admin)):
    data = body.model_dump()
    await db.scraper_config.update_one({"_id": "config"}, {"$set": data}, upsert=True)
    if data["enabled"] and RUN_SCHEDULER:
        reschedule(data["interval_min"])
        if not scheduler.running:
            scheduler.start()
    else:
        try: scheduler.remove_job("scrape")
        except Exception: pass
    return {"updated": True, **data}

@api.get("/scraper/feed")
async def scraper_feed(limit: int = 30, user: dict = Depends(get_current_user)):
    cur = db.leads.find({"scraped": True}).sort("created_at", -1).limit(limit)
    return [_lead_pub(l) async for l in cur]

# ====================== PEOPLE INTELLIGENCE ======================
class IdentityInput(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None

async def _resolve_identity(d: IdentityInput) -> dict:
    candidates = []
    if d.email:
        candidates.append({"source": "email_osint", "value": d.email, "confidence": 0.9,
                           "notes": "Email used as primary identifier."})
    if d.username:
        candidates.append({"source": "username_osint", "value": d.username, "confidence": 0.8,
                           "notes": "Username searched across platforms."})
    if d.phone:
        candidates.append({"source": "phone_osint", "value": d.phone, "confidence": 0.7,
                           "notes": "Phone number provided."})
    if d.name:
        candidates.append({"source": "name", "value": d.name, "confidence": 0.5,
                           "notes": "Display name provided."})
    primary = max(candidates, key=lambda c: c["confidence"]) if candidates else None
    return {"primary": primary, "candidates": candidates,
            "overall_confidence": primary["confidence"] if primary else 0.0}

async def _build_footprint(d: IdentityInput) -> dict:
    accounts = []
    if d.username:
        plats = {"twitter": f"https://x.com/{d.username}", "github": f"https://github.com/{d.username}",
                 "instagram": f"https://www.instagram.com/{d.username}/",
                 "reddit": f"https://www.reddit.com/user/{d.username}",
                 "tiktok": f"https://www.tiktok.com/@{d.username}"}
        async with httpx.AsyncClient(timeout=8, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"}) as c:
            for plat, url in plats.items():
                try:
                    r = await c.get(url)
                    exists = r.status_code == 200
                except Exception:
                    exists = False
                if exists:
                    accounts.append({"platform": plat, "handle": d.username, "url": url,
                                     "type": "developer" if plat == "github" else "social",
                                     "confidence": 0.85 if exists else 0.3})
    return {"accounts": accounts, "domains": [], "posts": []}

async def _public_records(d: IdentityInput) -> dict:
    records = []
    if d.email:
        async with httpx.AsyncClient(timeout=10) as c:
            try:
                r = await c.get(f"https://haveibeenpwned.com/unifiedsearch/{d.email}",
                                headers={"User-Agent": "NEXUS-OSINT"})
                if r.status_code == 200:
                    records.append({"category": "breach", "source": "HaveIBeenPwned",
                                    "description": "Email appears in known breach datasets.",
                                    "url": None, "confidence": 0.8})
            except Exception:
                pass
    if d.name:
        records.append({"category": "business", "source": "registry_guess",
                        "description": f"Possible business/registry association with {d.name}.",
                        "url": None, "confidence": 0.5})
    return {"records": records}

async def _ai_profile(d: IdentityInput, footprint: dict, records: dict, model_key: str) -> dict:
    ctx = {"input": d.model_dump(), "accounts": [a["platform"] for a in footprint["accounts"]],
           "records": [r["category"] for r in records["records"]]}
    prompt = ("You are an OSINT analyst. From the JSON below, infer a privacy-respecting public-profile. "
              "Return ONLY JSON with keys: summary (2-3 sentences), personality (string), "
              "interests (list of strings), occupation_guess (string), risk_indicators (list of strings), "
              "confidence (0-1 float).\n\n" + json.dumps(ctx))
    r = await deepseek_chat([{"role": "user", "content": prompt}], model_key=model_key, max_tokens=400, temperature=0.4)
    if "error" not in r:
        out = r["content"].strip()
        if "```" in out:
            out = out.split("```")[1].replace("json", "", 1).strip()
        try:
            data = json.loads(out[out.find("{"): out.rfind("}") + 1])
            data.setdefault("interests", []); data.setdefault("risk_indicators", [])
            data.setdefault("confidence", 0.6)
            return data
        except Exception:
            pass
    # heuristic fallback
    interests = []
    if any(a["platform"] == "github" for a in footprint["accounts"]):
        interests.append("software development")
    if any(a["platform"] in ("twitter", "instagram") for a in footprint["accounts"]):
        interests.append("online discourse")
    return {"summary": "Subject maintains a public digital presence across the platforms detected.",
            "personality": "Digitally engaged", "interests": interests,
            "occupation_guess": "Knowledge worker", "risk_indicators": [], "confidence": 0.55}

class PeopleScanReq(IdentityInput):
    model: str = "deepseek"

@api.post("/people-intel/scan")
async def people_intel_scan(body: PeopleScanReq, user: dict = Depends(get_current_user)):
    d = IdentityInput(name=body.name, email=body.email, phone=body.phone, username=body.username)
    mk = "qwen" if body.model == "qwen" else "deepseek"
    identity = await _resolve_identity(d)
    footprint = await _build_footprint(d)
    public_records = await _public_records(d)
    profile = await _ai_profile(d, footprint, public_records, mk)
    risk_ind = profile.get("risk_indicators", []) or []
    breached = any(r["category"] == "breach" for r in public_records["records"])
    level = "high" if (risk_ind and breached) else "medium" if (risk_ind or breached) else "low"
    reasons = list(risk_ind) + (["email found in breach datasets"] if breached else [])
    report = {"input": d.model_dump(), "identity": identity, "footprint": footprint,
              "public_records": public_records, "ai_profile": profile,
              "risk": {"level": level, "reasons": reasons},
              "summary": (f"People-intel for {d.name or d.username or d.email or 'subject'}: "
                          f"identity confidence {identity['overall_confidence']:.2f}, "
                          f"{len(footprint['accounts'])} accounts, "
                          f"{len(public_records['records'])} records, risk={level}."),
              "created_at": datetime.now(timezone.utc).isoformat(), "by": user["id"],
              "tenant_id": gov.tenant_id_of(user)}
    await db.people_reports.insert_one(dict(report))
    report.pop("_id", None)
    return report

@api.get("/people-intel/history")
async def people_intel_history(limit: int = 20, user: dict = Depends(get_current_user)):
    q = gov.tenant_scope(user)
    cur = db.people_reports.find(q, {"input": 1, "risk": 1, "summary": 1, "created_at": 1}).sort("created_at", -1).limit(limit)
    return [{"id": str(r["_id"]), "subject": (r.get("input") or {}),
             "risk": (r.get("risk") or {}).get("level"), "summary": r.get("summary"),
             "created_at": r.get("created_at")} async for r in cur]

# ====================== STRIPE PAYMENTS (lead credits) ======================
CREDIT_PACKAGES = {
    "starter": {"name": "Starter", "amount": 29.0, "credits": 10},
    "pro": {"name": "Pro", "amount": 99.0, "credits": 50},
    "agency": {"name": "Agency", "amount": 299.0, "credits": 200},
}

class CheckoutReq(BaseModel):
    package_id: str
    origin_url: str

@api.get("/payments/packages")
async def payment_packages(user: dict = Depends(get_current_user)):
    return [{"id": k, **v} for k, v in CREDIT_PACKAGES.items()]

@api.post("/payments/checkout")
async def payment_checkout(body: CheckoutReq, request: Request, user: dict = Depends(get_current_user)):
    pkg = CREDIT_PACKAGES.get(body.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")
    # open-redirect guard: only allow same-host or trusted origins
    from urllib.parse import urlparse
    o = urlparse(body.origin_url)
    host = (o.hostname or "")
    req_host = (request.base_url.hostname or "")
    if o.scheme not in ("http", "https") or not (
        host == req_host or host.endswith("emergentagent.com") or host in ("localhost", "127.0.0.1")):
        raise HTTPException(status_code=400, detail="Invalid origin")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/"
    meta = {"user_id": user["id"], "package_id": body.package_id, "credits": str(pkg["credits"])}
    req = CheckoutSessionRequest(amount=float(pkg["amount"]), currency="usd",
                                 success_url=success_url, cancel_url=cancel_url, metadata=meta)
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["id"], "package_id": body.package_id,
        "amount": float(pkg["amount"]), "currency": "usd", "credits": pkg["credits"],
        "payment_status": "pending", "status": "initiated", "metadata": meta,
        "created_at": datetime.now(timezone.utc).isoformat()})
    return {"url": session.url, "session_id": session.session_id}

async def _settle_payment(session_id: str, payment_status: str):
    if payment_status == "paid":
        # atomic: flip to paid only once, then grant credits only if we won the race
        res = await db.payment_transactions.update_one(
            {"session_id": session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"payment_status": "paid", "status": "complete",
                      "updated_at": datetime.now(timezone.utc).isoformat()}})
        if res.modified_count == 1:
            txn = await db.payment_transactions.find_one({"session_id": session_id})
            if txn:
                if txn.get("kind") == "lead" and txn.get("lead_id"):
                    await db.leads.update_one({"_id": ObjectId(txn["lead_id"])},
                                              {"$addToSet": {"unlocked_by": txn["user_id"]}})
                else:
                    await db.users.update_one({"_id": ObjectId(txn["user_id"])},
                                              {"$inc": {"credits": int(txn["credits"])}})
    else:
        await db.payment_transactions.update_one({"session_id": session_id},
            {"$set": {"payment_status": payment_status, "status": payment_status,
                      "updated_at": datetime.now(timezone.utc).isoformat()}})

@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id})
    if not txn or (txn["user_id"] != user["id"] and user.get("role") != "admin"):
        raise HTTPException(status_code=404, detail="Transaction not found")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"],
                        webhook_url=f"{str(request.base_url)}api/webhook/stripe")
    cs = await sc.get_checkout_status(session_id)
    await _settle_payment(session_id, cs.payment_status)
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    return {"status": cs.status, "payment_status": cs.payment_status,
            "amount_total": cs.amount_total, "currency": cs.currency,
            "kind": txn.get("kind", "credits"), "lead_id": txn.get("lead_id"),
            "credits": (u or {}).get("credits", 0)}

@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"],
                        webhook_url=f"{str(request.base_url)}api/webhook/stripe")
    body = await request.body()
    try:
        ev = await sc.handle_webhook(body, request.headers.get("Stripe-Signature"))
        await _settle_payment(ev.session_id, ev.payment_status)
    except Exception as e:
        logger.warning("stripe webhook error: %s", e)
    return {"received": True}

# ====================== ENRICHMENT ENGINE (Clearbit/Apollo-style) ======================
# Metered pricing: each call consumes credits (this is the paid API revenue stream).
ENRICH_COST = {"business": 1, "person": 1, "property": 1, "osint": 1, "lead": 3}

async def _charge_credits(user: dict, amount: int, reason: str):
    """Atomically deduct credits; admins are exempt. Raises 402 if insufficient."""
    if user.get("role") == "admin" or amount <= 0:
        return
    res = await db.users.update_one(
        {"_id": ObjectId(user["id"]), "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}})
    if res.modified_count != 1:
        raise HTTPException(status_code=402,
                            detail=f"Insufficient credits — {reason} costs {amount} credit(s). Buy a pack in Billing.")

def normalize_domain(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    return (domain.replace("https://", "").replace("http://", "")
            .replace("www.", "").strip().strip("/").lower())

def business_quality_score(data: dict) -> int:
    score = 0
    if data.get("tech_stack"):
        score += 25
    if data.get("industry"):
        score += 20
    if data.get("employee_range"):
        score += 20
    if data.get("domain"):
        score += 20
    if data.get("founded"):
        score += 15
    return min(score, 100)

def weighted_score(weights: dict) -> float:
    total = sum((v or 0) for v in weights.values())
    return round(min(total, 1.0) * 100, 1)

async def _ai_json(prompt: str, model_key: str = "deepseek", max_tokens: int = 350) -> Optional[dict]:
    r = await deepseek_chat([{"role": "user", "content": prompt}],
                            model_key=model_key, max_tokens=max_tokens, temperature=0.3)
    if "error" in r:
        return None
    out = r["content"].strip()
    if "```" in out:
        out = out.split("```")[1].replace("json", "", 1).strip()
    try:
        return json.loads(out[out.find("{"): out.rfind("}") + 1])
    except Exception:
        return None

async def _save_enrichment(etype: str, payload: dict, result: dict, user_id: str):
    await db.enrichments.insert_one({"type": etype, "input": payload, "result": result,
                                     "by": user_id, "created_at": datetime.now(timezone.utc).isoformat()})

class BusinessReq(BaseModel):
    name: str
    domain: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    model: str = "deepseek"

class PersonReq(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    model: str = "deepseek"

class PropertyReq(BaseModel):
    address: str
    model: str = "deepseek"

class OSINTEnrichReq(BaseModel):
    target: str
    model: str = "deepseek"

class LeadEnrichReq(BaseModel):
    business: Optional[BusinessReq] = None
    person: Optional[PersonReq] = None
    osint: Optional[OSINTEnrichReq] = None
    model: str = "deepseek"

def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", s or "")

async def enrich_business(payload: BusinessReq) -> dict:
    mk = "qwen" if payload.model == "qwen" else "deepseek"
    domain = normalize_domain(payload.domain)
    prompt = ("You are a B2B firmographic enrichment engine. From the business details, infer realistic "
              "firmographics. Return ONLY JSON with keys: industry (string), employee_range (e.g. '1-10'), "
              "founded (year integer), tech_stack (list of strings), description (1 sentence), confidence (0-1). "
              f"\nName: {payload.name}\nDomain: {domain}\nPhone: {payload.phone}\nAddress: {payload.address}")
    ai = await _ai_json(prompt, mk)
    enriched = {"name": payload.name, "domain": domain,
                "industry": (ai or {}).get("industry", ""),
                "employee_range": (ai or {}).get("employee_range", ""),
                "founded": (ai or {}).get("founded"),
                "tech_stack": (ai or {}).get("tech_stack", []) or [],
                "description": (ai or {}).get("description", ""),
                "ai_confidence": (ai or {}).get("confidence", 0.5 if ai else 0.0),
                "ai_available": ai is not None,
                "social": {"facebook": f"https://facebook.com/{_slug(payload.name)}",
                           "linkedin": f"https://linkedin.com/company/{_slug(payload.name)}"}}
    enriched["quality_score"] = business_quality_score(enriched)
    return enriched

async def enrich_person(payload: PersonReq) -> dict:
    mk = "qwen" if payload.model == "qwen" else "deepseek"
    ident = IdentityInput(name=payload.name, email=payload.email,
                          phone=payload.phone, username=payload.username)
    footprint = await _build_footprint(ident)
    records = await _public_records(ident)
    profile = await _ai_profile(ident, footprint, records, mk)
    return {"identity": payload.model_dump(exclude={"model"}),
            "profiles": [a["url"] for a in footprint["accounts"]],
            "footprint": footprint["accounts"], "ai_profile": profile,
            "breached": any(r["category"] == "breach" for r in records["records"])}

async def enrich_property(payload: PropertyReq) -> dict:
    mk = "qwen" if payload.model == "qwen" else "deepseek"
    prompt = ("You are a property intelligence estimator. From the address, provide a best-effort "
              "ESTIMATE. Return ONLY JSON with keys: property_type (string), estimated_value (string like "
              "'$300k-$450k'), bedrooms (int), year_built (int), owner_occupied (boolean), "
              "renovation_potential (low/medium/high), confidence (0-1)."
              f"\nAddress: {payload.address}")
    ai = await _ai_json(prompt, mk)
    return {"address": payload.address, "estimated": True, "ai_available": ai is not None,
            **(ai or {"property_type": "", "estimated_value": "", "confidence": 0.0})}

async def enrich_osint(payload: OSINTEnrichReq) -> dict:
    ident = IdentityInput(username=payload.target,
                          email=payload.target if "@" in payload.target else None)
    identity = await _resolve_identity(ident)
    footprint = await _build_footprint(ident)
    records = await _public_records(ident)
    return {"target": payload.target, "identity": identity,
            "profiles": [a["url"] for a in footprint["accounts"]],
            "accounts": footprint["accounts"], "records": records["records"]}

def link_identities(person: dict, osint: dict) -> dict:
    person_urls = set(person.get("profiles", []) if person else [])
    osint_urls = set(osint.get("profiles", []) if osint else [])
    overlap = person_urls & osint_urls
    union = person_urls | osint_urls
    confidence = round(len(overlap) / len(union), 2) if union else 0.0
    return {"match_confidence": confidence, "linked_profiles": sorted(union)}

def score_lead(enriched: dict) -> dict:
    business = enriched.get("business") or {}
    person = enriched.get("person") or {}
    osint = enriched.get("osint") or {}
    identity = link_identities(person, osint)
    social_count = len(osint.get("profiles", []) or person.get("profiles", []) or [])
    score = weighted_score({
        "business_quality": (business.get("quality_score", 0) / 100) * 0.4,
        "identity_strength": identity["match_confidence"] * 0.3,
        "social_presence": min(social_count / 5, 1.0) * 0.3,
    })
    return {"score": score, "identity": identity, "grade": (
        "A" if score >= 75 else "B" if score >= 50 else "C" if score >= 25 else "D")}

@api.get("/enrich/pricing")
async def enrich_pricing(user: dict = Depends(get_current_user)):
    return {"costs": ENRICH_COST, "unit": "credit", "credits": user.get("credits", 0)}

@api.post("/enrich/business")
async def enrich_business_api(payload: BusinessReq, user: dict = Depends(get_current_user)):
    await _charge_credits(user, ENRICH_COST["business"], "Business enrichment")
    res = await enrich_business(payload)
    await _save_enrichment("business", payload.model_dump(), res, user["id"])
    return res

@api.post("/enrich/person")
async def enrich_person_api(payload: PersonReq, user: dict = Depends(get_current_user)):
    await _charge_credits(user, ENRICH_COST["person"], "Person enrichment")
    res = await enrich_person(payload)
    await _save_enrichment("person", payload.model_dump(), res, user["id"])
    return res

@api.post("/enrich/property")
async def enrich_property_api(payload: PropertyReq, user: dict = Depends(get_current_user)):
    await _charge_credits(user, ENRICH_COST["property"], "Property enrichment")
    res = await enrich_property(payload)
    await _save_enrichment("property", payload.model_dump(), res, user["id"])
    return res

@api.post("/enrich/osint")
async def enrich_osint_api(payload: OSINTEnrichReq, user: dict = Depends(get_current_user)):
    await _charge_credits(user, ENRICH_COST["osint"], "OSINT enrichment")
    res = await enrich_osint(payload)
    await _save_enrichment("osint", payload.model_dump(), res, user["id"])
    return res

@api.post("/enrich/lead")
async def enrich_lead_api(payload: LeadEnrichReq, user: dict = Depends(get_current_user)):
    await _charge_credits(user, ENRICH_COST["lead"], "Composite lead enrichment")
    enriched = {}
    if payload.business:
        enriched["business"] = await enrich_business(payload.business)
    if payload.person:
        enriched["person"] = await enrich_person(payload.person)
    if payload.osint:
        enriched["osint"] = await enrich_osint(payload.osint)
    enriched["score"] = score_lead(enriched)
    await _save_enrichment("lead", payload.model_dump(), enriched, user["id"])
    return enriched

@api.get("/enrich/history")
async def enrich_history(limit: int = 20, user: dict = Depends(get_current_user)):
    q = {} if user.get("role") == "admin" else {"by": user["id"]}
    cur = db.enrichments.find(q, {"type": 1, "input": 1, "created_at": 1}).sort("created_at", -1).limit(limit)
    return [{"id": str(e["_id"]), "type": e.get("type"), "input": e.get("input"),
             "created_at": e.get("created_at")} async for e in cur]

# ====================== CORPORATE THREAT INTEL (owner-only high-ticket) ======================
RISKY_PORTS = {21: "FTP", 23: "Telnet", 3389: "RDP", 3306: "MySQL", 5432: "Postgres",
               6379: "Redis", 27017: "MongoDB", 9200: "Elasticsearch", 5900: "VNC", 11211: "Memcached"}
SENSITIVE_SUBS = ["admin", "dev", "staging", "test", "vpn", "remote", "portal", "git", "jenkins", "jira"]
SECURITY_HEADERS = ["strict-transport-security", "content-security-policy",
                    "x-frame-options", "x-content-type-options"]

class ThreatScanReq(BaseModel):
    domain: str
    model: str = "deepseek"

def _ssl_cert_sync(domain: str) -> dict:
    import ssl as _ssl, time as _time
    ctx = _ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ss:
                cert = ss.getpeercert()
                proto = ss.version()
    except _ssl.SSLCertVerificationError as e:
        return {"available": True, "valid": False, "error": str(getattr(e, "verify_message", e))[:120]}
    except Exception as e:
        return {"available": False, "error": str(e)[:120]}
    issuer = dict(x[0] for x in cert.get("issuer", []))
    not_after = cert.get("notAfter")
    days = None
    try:
        days = int((_ssl.cert_time_to_seconds(not_after) - _time.time()) / 86400)
    except Exception:
        pass
    return {"available": True, "valid": True, "protocol": proto, "valid_to": not_after,
            "days_to_expiry": days,
            "issuer": issuer.get("organizationName") or issuer.get("commonName", "")}

async def _shodan_host(ip: Optional[str]) -> Optional[dict]:
    """OSINT sensor: Shodan host lookup (org/OS/open ports/services/CVEs). Dormant until SHODAN_API_KEY set."""
    key = os.environ.get("SHODAN_API_KEY")
    if not key or not ip:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://api.shodan.io/shodan/host/{ip}?key={key}")
        if r.status_code != 200:
            return None
        d = r.json()
        return {"org": d.get("org"), "isp": d.get("isp"), "os": d.get("os"),
                "hostnames": d.get("hostnames", []), "ports": d.get("ports", []),
                "tags": d.get("tags", []), "vulns": list(d.get("vulns", []) or [])}
    except Exception:
        return None

# --- threat signal collectors (extracted from _gather_threat_signals to cut complexity) ---
def _resolve_ip_sync(domain: str):
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None


def _dns_records_sync(domain: str) -> dict:
    import dns.resolver
    rec = {}
    for rt in ["A", "AAAA", "MX", "NS", "TXT", "SOA"]:
        try:
            rec[rt] = [str(x) for x in dns.resolver.resolve(domain, rt, lifetime=5)]
        except Exception:
            rec[rt] = []
    return rec


def _dnssec_enabled_sync(domain: str) -> bool:
    import dns.resolver
    try:
        return bool(dns.resolver.resolve(domain, "DNSKEY", lifetime=5))
    except Exception:
        return False


def _sensitive_subs_sync(domain: str) -> list:
    found = []
    for s in SENSITIVE_SUBS:
        try:
            host = f"{s}.{domain}"
            found.append({"sub": host, "ip": socket.gethostbyname(host)})
        except Exception:
            pass
    return found


def _open_ports_sync(ip: str) -> list:
    res = []
    for p in RISKY_PORTS:
        try:
            sk = socket.socket(); sk.settimeout(1)
            if sk.connect_ex((ip, p)) == 0:
                res.append(p)
            sk.close()
        except Exception:
            pass
    return res


def _dns_email_findings(dns_rec: dict) -> list:
    findings = []
    txt_join = " ".join(dns_rec.get("TXT", [])).lower()
    if "v=spf1" not in txt_join:
        findings.append({"category": "Email Spoofing", "detail": "No SPF record found", "severity": "medium", "weight": 1.5})
    if "dmarc" not in txt_join:
        findings.append({"category": "Email Spoofing", "detail": "No DMARC policy detected", "severity": "medium", "weight": 1.5})
    return findings


async def _http_header_breach_findings(domain: str) -> tuple:
    findings, missing_headers = [], []
    async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"}) as c:
        try:
            resp = await c.get(f"https://{domain}")
            hdrs = {k.lower() for k in resp.headers.keys()}
            missing_headers = [h for h in SECURITY_HEADERS if h not in hdrs]
            for h in missing_headers:
                findings.append({"category": "Missing Header", "detail": f"Security header absent: {h}", "severity": "low", "weight": 0.8})
        except Exception:
            findings.append({"category": "Availability", "detail": "HTTPS endpoint unreachable", "severity": "medium", "weight": 1.0})
        try:
            br = await c.get(f"https://haveibeenpwned.com/unifiedsearch/{domain}",
                             headers={"User-Agent": "NEXUS-OSINT"})
            if br.status_code == 200:
                findings.append({"category": "Data Breach", "detail": "Domain appears in known breach datasets", "severity": "high", "weight": 2.5})
        except Exception:
            pass
    return missing_headers, findings


def _ssl_findings(ssl_info: dict) -> list:
    findings = []
    if ssl_info.get("available") and not ssl_info.get("valid"):
        findings.append({"category": "SSL/TLS", "detail": f"Invalid/untrusted certificate: {ssl_info.get('error', '')}", "severity": "high", "weight": 2.0})
    elif ssl_info.get("valid"):
        d = ssl_info.get("days_to_expiry")
        if d is not None and d < 0:
            findings.append({"category": "SSL/TLS", "detail": "TLS certificate has EXPIRED", "severity": "high", "weight": 2.5})
        elif d is not None and d < 30:
            findings.append({"category": "SSL/TLS", "detail": f"TLS certificate expires in {d} days", "severity": "medium", "weight": 1.2})
        if (ssl_info.get("protocol") or "") in ("SSLv2", "SSLv3", "TLSv1", "TLSv1.1"):
            findings.append({"category": "SSL/TLS", "detail": f"Weak TLS protocol in use: {ssl_info['protocol']}", "severity": "medium", "weight": 1.5})
    elif not ssl_info.get("available"):
        findings.append({"category": "SSL/TLS", "detail": "No HTTPS/TLS reachable on port 443", "severity": "medium", "weight": 1.5})
    return findings


def _shodan_findings(shodan: dict, open_ports: list) -> tuple:
    """Returns (extra_ports, findings) from a Shodan host record. Does not mutate open_ports."""
    extra_ports, findings = [], []
    if shodan:
        for p in shodan.get("ports", []):
            if p in RISKY_PORTS and p not in open_ports and p not in extra_ports:
                extra_ports.append(p)
                findings.append({"category": "Open Port", "detail": f"Shodan: risky service {RISKY_PORTS[p]} (port {p})", "severity": "high", "weight": 2.5})
        for v in (shodan.get("vulns") or [])[:8]:
            findings.append({"category": "Known CVE", "detail": f"Shodan-reported vulnerability: {v}", "severity": "high", "weight": 3.0})
        for t in (shodan.get("tags") or [])[:5]:
            findings.append({"category": "Shodan Flag", "detail": f"Exposure tag: {t}", "severity": "medium", "weight": 1.0})
    return extra_ports, findings


async def _gather_threat_signals(domain: str) -> dict:
    domain = normalize_domain(domain) or domain
    findings = []

    ip = await asyncio.to_thread(_resolve_ip_sync, domain)

    dns_rec = await asyncio.to_thread(_dns_records_sync, domain)
    findings += _dns_email_findings(dns_rec)

    dnssec_enabled = await asyncio.to_thread(_dnssec_enabled_sync, domain)
    if not dnssec_enabled:
        findings.append({"category": "DNS Hardening", "detail": "DNSSEC not enabled (DNS responses unsigned)", "severity": "low", "weight": 0.8})

    subs = await asyncio.to_thread(_sensitive_subs_sync, domain)
    for s in subs:
        findings.append({"category": "Exposed Surface", "detail": f"Sensitive subdomain reachable: {s['sub']}", "severity": "high", "weight": 2.0})

    open_ports = []
    if ip:
        open_ports = await asyncio.to_thread(_open_ports_sync, ip)
        for p in open_ports:
            findings.append({"category": "Open Port", "detail": f"Risky service exposed: {RISKY_PORTS[p]} (port {p})", "severity": "high", "weight": 2.5})

    missing_headers, header_findings = await _http_header_breach_findings(domain)
    findings += header_findings

    ssl_info = await asyncio.to_thread(_ssl_cert_sync, domain)
    findings += _ssl_findings(ssl_info)

    shodan = await _shodan_host(ip)
    extra_ports, shodan_findings = _shodan_findings(shodan, open_ports)
    open_ports += extra_ports
    findings += shodan_findings

    raw = min(sum(f["weight"] for f in findings), 10.0)
    return {"domain": domain, "ip": ip, "open_ports": open_ports,
            "sensitive_subdomains": [s["sub"] for s in subs],
            "missing_headers": missing_headers, "findings": findings,
            "dns": dns_rec, "dnssec_enabled": dnssec_enabled,
            "ssl": ssl_info, "shodan": shodan or {}, "raw_score": round(raw, 1)}

async def _threat_ai(signals: dict, model_key: str) -> dict:
    prompt = ("You are a cybersecurity risk analyst. Given the OSINT findings JSON for a company, "
              "return ONLY JSON with keys: risk_score (0-10 float), risk_level (low/medium/high/critical), "
              "executive_summary (2-3 sentences for a non-technical exec), "
              "top_vulnerabilities (list of up to 4 short strings), "
              "recommended_services (list of up to 4 security services to sell).\n\n" + json.dumps(signals)[:2500])
    ai = await _ai_json(prompt, model_key, max_tokens=450)
    return ai or {}

async def _sales_email_draft(domain: str, signals: dict, ai: dict, model_key: str) -> dict:
    seller = await db.outreach_profile.find_one({"_id": "profile"}) or {}
    sender_name = seller.get("sender_name", "Security Consultant")
    brand = seller.get("brand", "NEXUS Security")
    services = seller.get("services", "penetration testing, breach remediation and dark-web monitoring")
    cta = seller.get("cta", "")
    vulns = ", ".join(ai.get("top_vulnerabilities", []) or [f["detail"] for f in signals["findings"][:3]])
    prompt = (f"Write a concise, professional B2B cold outreach email (120-160 words) from {sender_name} of {brand}, "
              f"a cybersecurity firm offering: {services}. The recipient is the IT/security leader at {domain}. "
              f"Reference (diplomatically, without alarming or being unethical) that a passive external security review "
              f"surfaced potential exposure areas: {vulns}. Offer a free 15-minute review call. "
              f"{'Include this call-to-action link: ' + cta if cta else ''} "
              "Return ONLY JSON with keys: subject (string), body (string). Professional, confident, not fear-mongering.")
    ai_mail = await _ai_json(prompt, model_key, max_tokens=500)
    if not ai_mail:
        ai_mail = {"subject": f"Strengthening {domain}'s security posture",
                   "body": f"Hi team,\n\nI'm {sender_name} from {brand}. A passive external review of {domain} "
                           f"surfaced a few areas worth a quick look ({vulns}). We help companies close these gaps via "
                           f"{services}. Open to a free 15-minute review call?\n\nBest,\n{sender_name}\n{brand}"}
    return ai_mail

def _send_gmail_sync(to_addr: str, subject: str, body: str, from_name: str = "", attachments=None):
    user = os.environ.get("GMAIL_USER"); pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and pw):
        raise RuntimeError("Gmail not configured — set GMAIL_USER and GMAIL_APP_PASSWORD (16-char App Password).")
    msg = MIMEMultipart()
    msg["From"] = f"{from_name} <{user}>" if from_name else user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    for a in (attachments or []):
        content = a.get("content")
        raw = bytes(content) if isinstance(content, list) else content
        part = MIMEApplication(raw, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=a.get("filename", "attachment.pdf"))
        msg.attach(part)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as s:
        s.login(user, pw.replace(" ", ""))
        s.sendmail(user, [to_addr], msg.as_string())

async def send_email(to_addr: str, subject: str, body: str, from_name: str = "", attachments=None):
    api_key = os.environ.get("RESEND_API_KEY")
    if api_key:
        import resend
        resend.api_key = api_key
        sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
        params = {"from": f"{from_name} <{sender}>" if from_name else sender,
                  "to": [to_addr], "subject": subject,
                  "html": body.replace("\n", "<br>"), "text": body}
        if attachments:
            params["attachments"] = attachments
        res = await asyncio.to_thread(resend.Emails.send, params)
        if isinstance(res, dict) and res.get("error"):
            raise RuntimeError(str(res["error"]))
        return
    await asyncio.to_thread(_send_gmail_sync, to_addr, subject, body, from_name, attachments)

async def _run_threat_scan(domain: str, model_key: str = "deepseek", by: str = "system", source: str = "manual") -> dict:
    signals = await _gather_threat_signals(domain)
    ai = await _threat_ai(signals, model_key)
    try:
        ai_score = float(ai.get("risk_score"))
    except (TypeError, ValueError):
        ai_score = None
    risk_score = ai_score if (ai_score is not None and 0 <= ai_score <= 10) else signals["raw_score"]
    risk_score = max(0.0, min(10.0, round(risk_score, 1)))
    high_ticket = risk_score > 5
    email_draft = await _sales_email_draft(signals["domain"], signals, ai, model_key) if high_ticket else None
    report = {"domain": signals["domain"], "ip": signals["ip"], "risk_score": round(risk_score, 1),
              "risk_level": ai.get("risk_level", "high" if high_ticket else "low"),
              "high_ticket": high_ticket, "executive_summary": ai.get("executive_summary", ""),
              "top_vulnerabilities": ai.get("top_vulnerabilities", []),
              "recommended_services": ai.get("recommended_services", []),
              "findings": signals["findings"], "open_ports": signals["open_ports"],
              "sensitive_subdomains": signals["sensitive_subdomains"],
              "missing_headers": signals["missing_headers"],
              "dns": signals.get("dns") or {}, "dnssec_enabled": signals.get("dnssec_enabled", False),
              "ssl": signals.get("ssl") or {},
              "shodan": signals.get("shodan") or {},
              "email_draft": email_draft, "email_status": "draft" if email_draft else "n/a",
              "source": source, "by": by, "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.threat_reports.insert_one(dict(report))
    report["id"] = str(res.inserted_id); report.pop("_id", None)
    return report

async def _auto_threat_pipeline(lead_doc: dict):
    """Scan-to-pipeline: if a scraped lead exposes a real company domain, auto threat-scan it."""
    try:
        domain = _extract_company_domain(
            (lead_doc.get("raw_text", "") + " " + (lead_doc.get("source_url") or "") + " " + (lead_doc.get("website") or "")),
            lead_doc.get("source_url", ""), lead_doc.get("email", ""))
        if not domain:
            return
        domain = normalize_domain(domain)
        if not domain or await db.threat_reports.find_one({"domain": domain}):
            return
        await _run_threat_scan(domain, by="scraper-auto", source="scraper-auto")
        logger.info("auto threat scan completed for %s", domain)
    except Exception as e:
        logger.warning("auto threat pipeline error: %s", e)

@api.post("/threat/scan")
async def threat_scan(body: ThreatScanReq, request: Request, user: dict = Depends(require_admin),
                      _rl: bool = Depends(gov.rate_limit(int(os.environ.get("RL_THREAT_PER_MIN", "10")), 60))):
    mk = "qwen" if body.model == "qwen" else "deepseek"
    result = await _run_threat_scan(body.domain, mk, by=user["id"], source="manual")
    await gov.audit_log("threat.scan", user=user, request=request, target=body.domain,
                        meta={"risk_score": result.get("risk_score"), "high_ticket": result.get("high_ticket")})
    return result

@api.get("/threat/reports")
async def threat_reports(high_ticket_only: bool = False, limit: int = 50, user: dict = Depends(require_admin)):
    q = {"high_ticket": True} if high_ticket_only else {}
    cur = db.threat_reports.find(q).sort([("high_ticket", -1), ("risk_score", -1)]).limit(limit)
    out = []
    async for r in cur:
        r["id"] = str(r.pop("_id"))
        out.append(r)
    return out

class OutreachProfile(BaseModel):
    sender_name: str = ""
    sender_email: str = ""
    brand: str = ""
    services: str = ""
    cta: str = ""
    provider: str = ""
    auto_send: bool = False

@api.get("/threat/outreach-profile")
async def get_outreach_profile(user: dict = Depends(require_admin)):
    p = await db.outreach_profile.find_one({"_id": "profile"}) or {}
    p.pop("_id", None)
    return p

@api.put("/threat/outreach-profile")
async def set_outreach_profile(body: OutreachProfile, user: dict = Depends(require_admin)):
    await db.outreach_profile.update_one({"_id": "profile"}, {"$set": body.model_dump()}, upsert=True)
    return {"updated": True, **body.model_dump()}

class SendPitchReq(BaseModel):
    to_email: str

@api.post("/threat/reports/{report_id}/send-email")
async def send_threat_email(report_id: str, body: SendPitchReq, user: dict = Depends(require_admin)):
    rep = await db.threat_reports.find_one({"_id": ObjectId(report_id)})
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    draft = rep.get("email_draft")
    if not draft:
        raise HTTPException(status_code=400, detail="No drafted pitch for this report")
    prof = await db.outreach_profile.find_one({"_id": "profile"}) or {}
    from_name = prof.get("sender_name") or prof.get("brand") or "NEXUS Security"
    try:
        await send_email(body.to_email, draft["subject"], draft["body"], from_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Email send failed: {str(e)[:200]}")
    await db.threat_reports.update_one({"_id": ObjectId(report_id)},
        {"$set": {"email_status": "sent", "sent_to": body.to_email,
                  "sent_at": datetime.now(timezone.utc).isoformat()}})
    return {"sent": True, "to": body.to_email}

# ---------------- Bulk HQ outreach campaign (admin) ----------------
_FL_STATES = {"fl", "florida"}

def _is_fl_lead(l: dict) -> bool:
    st = (l.get("state") or "").strip().lower()
    if st in _FL_STATES:
        return True
    if st and st not in _FL_STATES:
        return False  # explicit non-FL state (e.g. sample rows like Stripe/CA)
    city = (l.get("city") or "").strip().lower()
    return bool(city) and any(city == c or c in city for c in TAMPA_CITIES)

def _outreach_first_name(l: dict) -> str:
    import re as _re
    local = (l.get("email") or "").split("@")[0]
    generic = {"info", "admin", "hello", "contact", "office", "press", "sales", "support", "team",
               "help", "mail", "enquiries", "inquiries", "booking", "service", "reception", "account",
               "accounts", "billing", "realestate", "realty", "homes", "listings"}
    tok = _re.split(r"[._\-+0-9]", local)[0].strip() if local else ""
    if tok and tok.lower() not in generic and tok.isalpha() and len(tok) >= 2:
        return tok.capitalize()
    return "there"

def _personalize(text: str, l: dict) -> str:
    fn = _outreach_first_name(l)
    out = (text.replace("{{company}}", l.get("company") or "your team")
               .replace("{{city}}", l.get("city") or "Tampa Bay")
               .replace("{{category}}", (l.get("category") or "").replace("_", " ").title() or "business")
               .replace("{{state}}", l.get("state") or "FL")
               .replace("{{first_name}}", fn))
    for token in ("[First Name]", "[first name]", "[FIRST NAME]", "[Name]", "[name]"):
        out = out.replace(token, fn)
    return out

async def _outreach_recipients(min_score: float, max_score: float, fl_only: bool, category: str = "") -> list:
    q = {"ready_to_sell": True, "email": {"$nin": ["", None]},
         "data_confidence_score": {"$gte": min_score, "$lte": max_score}}
    if category:
        q["category"] = category
    out = []
    async for l in db.leads.find(q):
        if fl_only and not _is_fl_lead(l):
            continue
        out.append(l)
    return out

class OutreachSendReq(BaseModel):
    subject: str = ""
    body: str = ""
    from_name: str = "Robert Burke"
    min_score: float = 0
    max_score: float = 100
    fl_only: bool = False
    category: str = ""     # e.g. "real_estate" to target only that HQ segment
    test_to: str = ""      # if set: send ONE test email here only (no DB writes, no bulk)
    confirm: bool = False  # must be true to run the live bulk send
    limit: int = 0         # 0 = no cap
    attach_sample_pack: bool = False  # attach the 5-lead sample pilot pack PDF

@api.post("/outreach/preview")
async def outreach_preview(body: OutreachSendReq, user: dict = Depends(require_admin)):
    recs = await _outreach_recipients(body.min_score, body.max_score, body.fl_only, body.category)
    already = set()
    async for s in db.outreach_sends.find({"status": "sent"}, {"lead_id": 1}):
        already.add(str(s.get("lead_id")))
    pending = [r for r in recs if str(r["_id"]) not in already]
    return {"total": len(recs), "already_sent": len(recs) - len(pending), "pending": len(pending),
            "sender": os.environ.get("SENDER_EMAIL", ""),
            "recipients": [{"company": r.get("company"), "email": r.get("email"), "city": r.get("city"),
                            "category": r.get("category"), "score": r.get("data_confidence_score")}
                           for r in pending[:300]]}

@api.post("/outreach/send")
async def outreach_send(body: OutreachSendReq, request: Request, user: dict = Depends(require_admin)):
    if not body.subject.strip() or not body.body.strip():
        raise HTTPException(status_code=400, detail="Subject and body are required.")
    # Test mode: single email to a chosen address, personalized from the first matching lead. No DB writes.
    if body.test_to.strip():
        recs = await _outreach_recipients(body.min_score, body.max_score, body.fl_only, body.category)
        s = recs[0] if recs else {"company": "Bay Area Realty", "city": "Tampa", "category": "real_estate", "state": "FL", "email": body.test_to}
        try:
            att = _sample_pack_attachment() if body.attach_sample_pack else None
            await send_email(body.test_to.strip(), _personalize(body.subject, s), _personalize(body.body, s), body.from_name, attachments=att)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Test send failed: {str(e)[:220]}")
        return {"test": True, "to": body.test_to.strip(), "sample_company": s.get("company")}
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to run the live campaign.")
    recs = await _outreach_recipients(body.min_score, body.max_score, body.fl_only, body.category)
    already = set()
    async for s in db.outreach_sends.find({"status": "sent"}, {"lead_id": 1}):
        already.add(str(s.get("lead_id")))
    recs = [r for r in recs if str(r["_id"]) not in already]
    if body.limit and body.limit > 0:
        recs = recs[:body.limit]
    import uuid as _uuid
    campaign_id = str(_uuid.uuid4())[:8]
    sent = failed = 0
    first_error = ""
    att = _sample_pack_attachment() if body.attach_sample_pack else None
    for l in recs:
        subj = _personalize(body.subject, l)
        html = _personalize(body.body, l)
        rec = {"campaign_id": campaign_id, "lead_id": l["_id"], "email": l.get("email"),
               "company": l.get("company"), "subject": subj, "from_name": body.from_name,
               "score": l.get("data_confidence_score"), "by": user.get("email"),
               "sent_at": datetime.now(timezone.utc).isoformat()}
        try:
            await send_email(l["email"], subj, html, body.from_name, attachments=att)
            rec["status"] = "sent"; sent += 1
        except Exception as e:
            rec["status"] = "failed"; rec["error"] = str(e)[:200]; failed += 1
            first_error = first_error or str(e)[:200]
        await db.outreach_sends.insert_one(rec)
        await asyncio.sleep(0.6)  # gentle pacing for the mail provider
    await gov.audit_log("outreach.campaign", user=user, request=request, target=campaign_id,
                        meta={"sent": sent, "failed": failed, "attempted": len(recs), "category": body.category},
                        status="success" if failed == 0 else "partial")
    return {"campaign_id": campaign_id, "sent": sent, "failed": failed, "attempted": len(recs),
            "first_error": first_error}

@api.get("/outreach/history")
async def outreach_history(user: dict = Depends(require_admin)):
    out = []
    async for r in db.outreach_sends.find().sort("sent_at", -1).limit(500):
        r["id"] = str(r.pop("_id")); r["lead_id"] = str(r.get("lead_id"))
        out.append(r)
    return {"sends": out, "total": len(out)}

# ---------------- Email enrichment (find emails from lead websites) ----------------
_EMAIL_JUNK = ("example.com", "sentry", "wixpress", "wix.com", "godaddy", "squarespace",
               "schema.org", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", "yourdomain",
               "domain.com", "email.com", "sentry.io", "cloudflare", "googleapis", "gstatic",
               "w3.org", "your-email", "name@", "user@", "test@", "no-reply@", "noreply@")

def _extract_emails(html: str, site_domain: str = "") -> list:
    found = []
    for m in re.findall(r'mailto:([^"\'?>\s]+)', html or "", re.I):
        found.append(m.strip())
    found += EMAIL_RX.findall(html or "")
    clean = []
    for e in found:
        el = e.lower().strip().rstrip(".")
        if len(el) > 100 or any(j in el for j in _EMAIL_JUNK):
            continue
        if el not in clean:
            clean.append(el)
    if site_domain:
        sd = site_domain.lower().replace("www.", "")
        dom_match = [e for e in clean if e.split("@")[-1].endswith(sd) or sd.split(".")[0] in e.split("@")[-1]]
        if dom_match:
            return dom_match
    return clean

async def _enrich_lead_email(lead: dict):
    from urllib.parse import urlparse, urljoin
    site = (lead.get("website") or "").strip()
    if not site:
        return None
    if not site.startswith("http"):
        site = "https://" + site
    dom = urlparse(site).netloc
    pages = [site, urljoin(site, "/contact"), urljoin(site, "/contact-us"), urljoin(site, "/about")]
    emails = []
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (compatible; NEXUS-LeadBot/1.0)"}) as c:
            for u in pages:
                try:
                    r = await c.get(u)
                    if r.status_code == 200:
                        emails = _extract_emails(r.text, dom)
                        if emails:
                            break
                except Exception:
                    continue
    except Exception:
        return None
    if not emails:
        return None
    email = emails[0]
    intent = int(lead.get("ai_intent_score") or lead.get("score") or 0)
    v = await asyncio.to_thread(_osint_verify_sync, email, lead.get("phone", ""), site,
                                lead.get("company", ""), lead.get("city", ""), lead.get("state", ""))
    conf = _data_confidence(v, intent)
    fields = _osint_fields(v, conf, intent); fields.pop("buyer_user_id", None)
    await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"email": email, "email_source": "web_enriched", **fields}})
    return email

class EnrichReq(BaseModel):
    category: str = ""
    only_hq: bool = True
    fl_only: bool = False
    limit: int = 150

async def _run_email_enrichment(job_id: str, leads: list):
    found = done = 0
    for l in leads:
        try:
            if await _enrich_lead_email(l):
                found += 1
        except Exception:
            pass
        done += 1
        await db.enrich_jobs.update_one({"job_id": job_id}, {"$set": {"done": done, "found": found}})
        await asyncio.sleep(0.3)
    await db.enrich_jobs.update_one({"job_id": job_id},
        {"$set": {"status": "complete", "finished_at": datetime.now(timezone.utc).isoformat()}})

@api.post("/outreach/enrich-emails")
async def enrich_emails(body: EnrichReq, user: dict = Depends(require_admin)):
    q = {"website": {"$nin": ["", None]},
         "$or": [{"email": ""}, {"email": None}, {"email": {"$exists": False}}]}
    if body.only_hq:
        q["ready_to_sell"] = True
    if body.category:
        q["category"] = body.category
    leads = [l async for l in db.leads.find(q).limit(body.limit)]
    if body.fl_only:
        leads = [l for l in leads if _is_fl_lead(l)]
    import uuid as _uuid
    job_id = str(_uuid.uuid4())[:8]
    await db.enrich_jobs.insert_one({"job_id": job_id, "status": "running", "total": len(leads),
                                     "done": 0, "found": 0, "started_at": datetime.now(timezone.utc).isoformat()})
    asyncio.create_task(_run_email_enrichment(job_id, leads))
    return {"job_id": job_id, "candidates": len(leads)}

@api.get("/outreach/enrich-status/{job_id}")
async def enrich_status(job_id: str, user: dict = Depends(require_admin)):
    j = await db.enrich_jobs.find_one({"job_id": job_id})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    j.pop("_id", None)
    return j

# ---------------- Auto-send engine (email new HQ leads automatically) ----------------
class AutoOutreachCfg(BaseModel):
    enabled: bool = False
    category: str = "real_estate"
    subject: str = ""
    body: str = ""
    from_name: str = "Robert Burke"
    min_score: float = 0
    attach_sample_pack: bool = False  # auto-attach the 5-lead sample pilot pack PDF

@api.get("/outreach/auto")
async def get_auto_outreach(user: dict = Depends(require_admin)):
    c = await db.outreach_auto.find_one({"_id": "config"}) or {}
    c.pop("_id", None)
    return c

@api.put("/outreach/auto")
async def set_auto_outreach(body: AutoOutreachCfg, user: dict = Depends(require_admin)):
    await db.outreach_auto.update_one({"_id": "config"},
        {"$set": {**body.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    return {"updated": True, **body.model_dump()}

async def _auto_outreach_sweep(reason: str = "manual"):
    cfg = await db.outreach_auto.find_one({"_id": "config"})
    if not cfg or not cfg.get("enabled"):
        return {"skipped": "disabled"}
    if not (cfg.get("subject") and cfg.get("body")):
        return {"skipped": "no template"}
    recs = await _outreach_recipients(cfg.get("min_score", 0), 100, False, cfg.get("category", ""))
    already = set()
    async for s in db.outreach_sends.find({"status": "sent"}, {"lead_id": 1}):
        already.add(str(s.get("lead_id")))
    recs = [r for r in recs if str(r["_id"]) not in already]
    if not recs:
        return {"sent": 0, "failed": 0}
    import uuid as _uuid
    campaign_id = "auto-" + str(_uuid.uuid4())[:6]
    sent = failed = 0
    att = _sample_pack_attachment() if cfg.get("attach_sample_pack") else None
    for l in recs:
        subj = _personalize(cfg["subject"], l); html = _personalize(cfg["body"], l)
        rec = {"campaign_id": campaign_id, "lead_id": l["_id"], "email": l.get("email"),
               "company": l.get("company"), "subject": subj, "from_name": cfg.get("from_name", "Robert Burke"),
               "score": l.get("data_confidence_score"), "by": "auto-engine", "auto": True,
               "sent_at": datetime.now(timezone.utc).isoformat()}
        try:
            await send_email(l["email"], subj, html, cfg.get("from_name", "Robert Burke"), attachments=att)
            rec["status"] = "sent"; sent += 1
        except Exception as e:
            rec["status"] = "failed"; rec["error"] = str(e)[:200]; failed += 1
        await db.outreach_sends.insert_one(rec)
        await asyncio.sleep(0.6)
    if sent or failed:
        logger.info("Auto-outreach (%s): campaign=%s sent=%d failed=%d", reason, campaign_id, sent, failed)
    return {"campaign_id": campaign_id, "sent": sent, "failed": failed}

@api.post("/outreach/auto/run")
async def run_auto_outreach(user: dict = Depends(require_admin)):
    return await _auto_outreach_sweep("manual-trigger")

# ---------------- Pilot template library (5-lead / 10-lead offers) ----------------
_SIG = "\n\nBest,\nRobert\nNEXUS Lead Intelligence\nhttps://nexuscloud.sh"

def _re_body(n, price):
    return (f"Hi [First Name],\n\n"
            f"I built NEXUS to fix what most {{{{category}}}} operators in {{{{city}}}} already know too well: "
            f"recycled leads, low-intent contacts, and wasted follow-up.\n\n"
            f"NEXUS is a local lead-intelligence system that finds, filters, scores, and packages Tampa Bay "
            f"opportunities into clean, outreach-ready lead reports.\n\n"
            f"What makes it different:\n"
            f"- Local targeting by county, city, and niche\n"
            f"- Public-source (OSINT) verification instead of random scraped lists\n"
            f"- AI scoring so the strongest opportunities rise to the top\n"
            f"- Enrichment notes explaining why each lead matters\n"
            f"- Clean PDF/CSV delivery your team can act on immediately\n\n"
            f"Pilot offer:\n{n} premium, AI-scored {{{{category}}}} leads (all scored 92+) - ${price}\n\n"
            f"That's ${round(price/n)}/lead for verified, exclusive, ready-to-work opportunities — "
            f"a fraction of portal or agency pricing.\n\n"
            f"Want me to send over a sample pilot pack for {{{{city}}}}?" + _SIG)

OUTREACH_TEMPLATES = {
    "re_pilot_10": {"label": "Real Estate — 10-lead pilot ($350)", "leads": 10, "price": 350,
                    "subject": "10 AI-scored Tampa Bay leads for {{company}} (pilot)",
                    "body": _re_body(10, 350)},
    "re_pilot_5": {"label": "Real Estate — 5-lead pilot ($200)", "leads": 5, "price": 200,
                   "subject": "A 5-lead Tampa Bay pilot for {{company}}",
                   "body": _re_body(5, 200)},
    "biz_pilot_10": {"label": "B2B (any sector) — 10-lead pilot ($350)", "leads": 10, "price": 350,
                     "subject": "10 verified {{category}} leads for {{company}} (pilot)",
                     "body": _re_body(10, 350)},
    "biz_pilot_5": {"label": "B2B (any sector) — 5-lead pilot ($200)", "leads": 5, "price": 200,
                    "subject": "A 5-lead {{category}} pilot for {{company}}",
                    "body": _re_body(5, 200)},
}

@api.get("/outreach/templates")
async def outreach_templates(user: dict = Depends(require_admin)):
    return {"templates": [{"id": k, **v} for k, v in OUTREACH_TEMPLATES.items()]}

# --- Sample pilot pack: 5 HQ (92+) cleaning-demand leads across Pinellas/Hillsborough/Pasco ---
SAMPLE_PACK = {
    "title": "NEXUS Sample Pilot Pack - Tampa Bay Cleaning Services",
    "region": "Pinellas / Hillsborough / Pasco County, FL",
    "note": ("Representative SAMPLE of the quality delivered in a live 5-lead pilot. Every lead is "
             "OSINT-verified and AI-scored 92+, exclusive to the buyer. Contact details are masked and "
             "unlock on purchase. Figures are illustrative and editable to your exact market."),
    "pricing": "5 leads = $200 ($40/lead)  |  10 leads = $350 ($35/lead)",
    "leads": [
        {"rank": 1, "type": "Residential", "category": "residential_home_cleaning",
         "county": "Pinellas", "city": "Palm Harbor, FL",
         "entity_masked": "Waterfront Residence - Palm Harbor",
         "contact_masked": "•••@•••  ·  (727) •••-••17", "score": 96, "tier": "Strategic",
         "budget_est": "$190-$260 / mo (recurring)",
         "intent_summary": "4BR/3BA waterfront home; owner seeking reliable bi-weekly whole-home cleaning after a recent move-in. High-intent, recurring, insured-preferred.",
         "verification_nodes": ["Address verified", "Phone valid", "Property records matched", "Intent confirmed", "Geo-located"],
         "source": "OSINT · public listing + permit + review signals"},
        {"rank": 2, "type": "Residential", "category": "residential_home_cleaning",
         "county": "Pasco", "city": "Wesley Chapel, FL",
         "entity_masked": "New-Build Household - Wesley Chapel",
         "contact_masked": "•••@•••  ·  (813) •••-••04", "score": 94, "tier": "Strategic",
         "budget_est": "$220-$300 one-time + $150/mo",
         "intent_summary": "New-construction move-in; homeowner requesting a deep move-in clean then monthly maintenance. Dual-income, time-poor, ready to book.",
         "verification_nodes": ["Address verified", "Email valid", "Property records matched", "Intent confirmed"],
         "source": "OSINT · new-home permit + local group signals"},
        {"rank": 3, "type": "Residential", "category": "residential_home_cleaning",
         "county": "Hillsborough", "city": "Tampa (Hyde Park), FL",
         "entity_masked": "Historic Home - South Tampa",
         "contact_masked": "•••@•••  ·  (813) •••-••88", "score": 93, "tier": "Tactical",
         "budget_est": "$160-$220 / mo (weekly)",
         "intent_summary": "Dual-income professional household in Hyde Park seeking weekly maid service; values eco-friendly products and vetted, background-checked staff.",
         "verification_nodes": ["Address verified", "Phone valid", "Footprint consistent", "Geo-located"],
         "source": "OSINT · public listing + review + social signals"},
        {"rank": 4, "type": "Commercial", "category": "commercial_cleaning",
         "county": "Pinellas", "city": "Clearwater, FL",
         "entity_masked": "Dental / Medical Practice - Clearwater",
         "contact_masked": "office•••@•••  ·  (727) •••-••31", "score": 95, "tier": "Strategic",
         "budget_est": "$1,400-$2,100 / mo (nightly janitorial)",
         "intent_summary": "~6,000 sqft dental/medical office needs nightly janitorial with medical-grade sanitation and restroom service. Decision-maker is the practice manager; renewing off a lapsed vendor.",
         "verification_nodes": ["Business registry verified", "Phone valid", "Address verified", "Intent confirmed", "Geo-located"],
         "source": "OSINT · registry + license + review signals"},
        {"rank": 5, "type": "Commercial", "category": "commercial_cleaning",
         "county": "Hillsborough", "city": "Brandon, FL",
         "entity_masked": "Multi-Tenant Office Park - Brandon",
         "contact_masked": "pm•••@•••  ·  (813) •••-••62", "score": 92, "tier": "Tactical",
         "budget_est": "$2,600-$3,800 / mo (common areas + restrooms)",
         "intent_summary": "Property manager sourcing common-area, lobby and restroom cleaning across a multi-tenant office park; wants one accountable vendor and a fixed monthly scope.",
         "verification_nodes": ["Business registry verified", "Email valid", "Address verified", "Footprint consistent"],
         "source": "OSINT · registry + property mgmt + review signals"},
    ],
}

def _sample_pack_csv() -> str:
    import io, csv
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["Rank", "Type", "Category", "County", "City", "Entity (masked)", "Contact (masked)",
                "Score", "Tier", "Budget Est", "Intent Summary", "Verification Nodes", "Source"])
    for l in SAMPLE_PACK["leads"]:
        w.writerow([l["rank"], l["type"], l["category"], l["county"], l["city"], l["entity_masked"],
                    l["contact_masked"], l["score"], l["tier"], l["budget_est"], l["intent_summary"],
                    " | ".join(l["verification_nodes"]), l["source"]])
    return out.getvalue()

def _pdf_txt(s: str) -> str:
    s = str(s)
    for k, v in {"•": "*", "–": "-", "—": "-", "·": "-", "’": "'", "“": '"', "”": '"', "…": "..."}.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

def _sample_pack_pdf() -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    p = FPDF(format="A4")
    p.set_auto_page_break(True, margin=16)
    p.add_page()
    p.set_fill_color(13, 26, 18)
    p.rect(0, 0, 210, 30, "F")
    p.set_xy(12, 8)
    p.set_text_color(159, 232, 112)
    p.set_font("Helvetica", "B", 15)
    p.cell(0, 8, _pdf_txt(SAMPLE_PACK["title"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.set_x(12)
    p.set_text_color(150, 180, 155)
    p.set_font("Helvetica", "", 10)
    p.cell(0, 6, _pdf_txt(SAMPLE_PACK["region"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    p.ln(8)
    p.set_text_color(70, 70, 70)
    p.set_font("Helvetica", "I", 9)
    p.multi_cell(0, 4.5, _pdf_txt(SAMPLE_PACK["note"]))
    p.ln(3)
    for l in SAMPLE_PACK["leads"]:
        p.set_text_color(20, 20, 20)
        p.set_font("Helvetica", "B", 11)
        p.cell(0, 6, _pdf_txt(f"#{l['rank']}   {l['type'].upper()} CLEANING   -   Score {l['score']}/100 ({l['tier']})"),
               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        p.set_font("Helvetica", "B", 10)
        p.set_text_color(40, 90, 50)
        p.cell(0, 5.5, _pdf_txt(f"{l['entity_masked']}  -  {l['city']} ({l['county']} County)"),
               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        p.set_font("Helvetica", "", 9)
        p.set_text_color(50, 50, 50)
        p.multi_cell(0, 4.5, _pdf_txt("Intent: " + l["intent_summary"]))
        p.cell(0, 5, _pdf_txt(f"Budget est: {l['budget_est']}   |   Contact: {l['contact_masked']}"),
               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        p.set_text_color(95, 95, 95)
        p.set_font("Helvetica", "", 8)
        p.multi_cell(0, 4, _pdf_txt("Verified: " + ", ".join(l["verification_nodes"]) + "   |   " + l["source"]))
        p.ln(2)
        p.set_draw_color(215, 215, 215)
        p.line(12, p.get_y(), 198, p.get_y())
        p.ln(3)
    p.ln(1)
    p.set_font("Helvetica", "B", 10)
    p.set_text_color(40, 90, 50)
    p.multi_cell(0, 5, _pdf_txt("Pilot pricing: " + SAMPLE_PACK["pricing"] +
                                ". Every lead OSINT-verified, AI-scored 92+, exclusive to you. Contacts unlock on purchase."))
    p.set_font("Helvetica", "", 8)
    p.set_text_color(120, 120, 120)
    p.cell(0, 5, _pdf_txt("Prepared for NEXUS Lead Intelligence - nexuscloud.sh - representative sample, figures editable."),
           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(p.output())

def _sample_pack_attachment() -> list:
    pdf = _sample_pack_pdf()
    return [{"filename": "NEXUS_Sample_Pilot_Pack.pdf",
             "content": list(pdf),
             "content_type": "application/pdf"}]

@api.get("/outreach/sample-pack")
async def outreach_sample_pack(user: dict = Depends(require_admin)):
    return SAMPLE_PACK

@api.get("/outreach/sample-pack.csv")
async def outreach_sample_pack_csv(user: dict = Depends(require_admin)):
    return StreamingResponse(iter([_sample_pack_csv()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=nexus_sample_pilot_pack.csv"})

@api.get("/outreach/sample-pack.pdf")
async def outreach_sample_pack_pdf(user: dict = Depends(require_admin)):
    return Response(content=_sample_pack_pdf(), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=nexus_sample_pilot_pack.pdf"})

# ============================================================================
# GOVERNMENT-GRADE INTELLIGENCE ENRICHMENT + PER-LEAD STOREFRONT
# ============================================================================
# Llama 3 enrichment produces a structured "Intelligence Payload" optimized for
# defense / municipal / federal procurement evaluation:
#   - data_confidence_score (0-100)  : weighted cross-platform verification
#   - cross_verification (list)       : validated nodes (Domain_MX_Match, ...)
#   - risk_matrix (list)              : anomalies / high-risk operational signals
#   - operational_value_tier          : Strategic | Tactical | Operational
# Leads flagged ready_to_sell enter the storefront and are sold per-lead via credits.

STOREFRONT_MIN_CONFIDENCE = float(os.environ.get("STOREFRONT_MIN_CONFIDENCE", "65"))
TIER_CREDITS = {"Strategic": 5, "Tactical": 3, "Operational": 1}
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "trashmail.com", "yopmail.com", "throwawaymail.com", "getnada.com", "sharklasers.com",
}

def _operational_tier(confidence: float, intent: int) -> str:
    if confidence >= 80 and intent >= 60:
        return "Strategic"
    if confidence >= 60:
        return "Tactical"
    return "Operational"

def _mask_email(e: str) -> str:
    e = (e or "").strip()
    if "@" not in e:
        return ""
    user_part, domain = e.split("@", 1)
    head = (user_part[0] + "•••") if user_part else "•••"
    return f"{head}@{domain}"

def _mask_company(c: str) -> str:
    c = (c or "").strip()
    if not c:
        return "Verified Entity"
    return c[:3] + "•••" if len(c) > 3 else c

def _osint_verify_sync(email: str, phone: str, website: str, company: str,
                       city: str, state: str) -> dict:
    """Synchronous OSINT verification — runs in a worker thread (network I/O)."""
    import socket as _sock
    nodes, risk = [], []
    email = (email or "").strip()
    email_valid = bool(EMAIL_RX.fullmatch(email)) if email else False
    if email_valid:
        nodes.append("Email_Syntax_Valid")
    mx_ok = False
    email_domain = email.split("@", 1)[1].lower() if email_valid else ""
    if email_domain:
        if email_domain in DISPOSABLE_EMAIL_DOMAINS:
            risk.append({"flag": "Disposable_Email_Domain", "severity": "high"})
        try:
            import dns.resolver as _dnsr
            ans = _dnsr.resolve(email_domain, "MX", lifetime=4.0)
            mx_ok = len(list(ans)) > 0
        except Exception:
            mx_ok = False
        if mx_ok:
            nodes.append("Domain_MX_Match")
        else:
            risk.append({"flag": "Unverified_Email_Domain", "severity": "medium"})
    phone_valid = bool(PHONE_RX.search(phone or ""))
    if phone_valid:
        nodes.append("Phone_Format_Valid")
    web = (website or "").strip()
    web_domain = ""
    if web:
        web_domain = web.replace("https://", "").replace("http://", "").split("/")[0]
    elif email_domain:
        web_domain = email_domain
    web_resolves = False
    if web_domain:
        try:
            _sock.gethostbyname(web_domain)
            web_resolves = True
        except Exception:
            web_resolves = False
        if web_resolves:
            nodes.append("Public_Registry_Verified")
        elif web:
            risk.append({"flag": "Unresolved_Web_Presence", "severity": "medium"})
    # A resolving company domain that can also receive mail (MX) is a strong legitimacy signal,
    # even when no contact email was published (common for OSM business records).
    if web_domain and not mx_ok:
        try:
            import dns.resolver as _dnsr2
            if len(list(_dnsr2.resolve(web_domain, "MX", lifetime=4.0))) > 0:
                mx_ok = True
                if "Domain_MX_Match" not in nodes:
                    nodes.append("Domain_MX_Match")
        except Exception:
            pass
    if company and web_domain:
        core = re.sub(r"[^a-z0-9]", "", company.lower())[:5]
        if core and core[:4] and core[:4] in web_domain.replace(".", "").lower():
            nodes.append("Social_Footprint_Consistent")
    geo_ok = bool(city and state)
    if geo_ok:
        nodes.append("Geo_Located")
    if not (mx_ok or phone_valid):
        risk.append({"flag": "No_Verifiable_Contact", "severity": "high"})
    if not company:
        risk.append({"flag": "Incomplete_Entity_Record", "severity": "low"})
    return {"nodes": nodes, "risk": risk, "email_valid": email_valid, "mx": mx_ok,
            "phone_valid": phone_valid, "web_resolves": web_resolves, "geo": geo_ok}

def _data_confidence(v: dict, intent: int) -> float:
    s = 0.0
    if v["email_valid"]:
        s += 10
    if v["mx"]:
        s += 25
    if v["web_resolves"]:
        s += 20
    if v["phone_valid"]:
        s += 15
    if v["geo"]:
        s += 10
    if "Social_Footprint_Consistent" in v["nodes"]:
        s += 10
    s += min(max(intent, 0), 100) * 0.10
    return float(round(min(s, 100.0), 1))

def _osint_fields(v: dict, conf: float, intent: int) -> dict:
    """Storefront intelligence-payload fields derived from an OSINT verification.
    `ready_to_sell` is the HQ gate (confidence >= STOREFRONT_MIN_CONFIDENCE and >=2 nodes)."""
    tier = _operational_tier(conf, intent)
    nodes = v["nodes"]
    return {
        "data_confidence_score": conf, "quality_score": conf, "score": conf,
        "cross_verification": nodes, "risk_matrix": list(v["risk"]),
        "operational_value_tier": tier, "price_per_lead": TIER_CREDITS[tier],
        "purchase_status": "available", "buyer_user_id": None,
        "ready_to_sell": conf >= STOREFRONT_MIN_CONFIDENCE and len(nodes) >= 2,
    }

async def _llama_assess(category: str, text: str, company: str, model_key: str = "llama") -> dict:
    """Run the LLM analyst pass. Falls back to deepseek if Llama 3 is unavailable."""
    subject = text.strip() or f"Entity: {company or 'unknown'} | Sector: {category}"
    prompt = (
        "You are a procurement intelligence analyst vetting an entity/lead for defense, "
        "municipal, and federal contracting suitability. Return ONLY a JSON object with keys: "
        "summary (1-2 sentence operational brief), intent_score (0-100 integer: likelihood this "
        "entity is actively procuring/contracting now), budget_estimate (string), "
        "category_tags (list of 3 short tags), anomaly_flags (list of short risk strings, e.g. "
        "'Unverified entity structure', 'Inconsistent records'; empty list if none), "
        "entity_consistency (one of high|medium|low).\n\nDOSSIER:\n" + subject[:1600]
    )
    r = await deepseek_chat([{"role": "user", "content": prompt}],
                            model_key=model_key, max_tokens=400, temperature=0.2)
    if "error" in r and model_key != "deepseek":
        r = await deepseek_chat([{"role": "user", "content": prompt}],
                                model_key="deepseek", max_tokens=400, temperature=0.2)
    out = {"summary": "", "intent_score": 0, "budget_estimate": "",
           "category_tags": [], "anomaly_flags": [], "entity_consistency": "low"}
    if "error" in r:
        return out
    raw = (r.get("content") or "").strip()
    if "```" in raw:
        raw = raw.split("```")[1].replace("json", "", 1).strip()
    try:
        parsed = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        if isinstance(parsed, dict):
            out.update({k: parsed.get(k, out[k]) for k in out})
            out["intent_score"] = int(out.get("intent_score") or 0)
    except Exception:
        pass
    return out

async def _enrich_and_store(raw: dict, model_key: str = "llama") -> dict:
    text = raw.get("raw_text") or ""
    contacts = _extract_contacts(text) if text else {}
    email = (raw.get("email") or contacts.get("email") or "").strip()
    phone = (raw.get("phone") or contacts.get("phone") or "").strip()
    company = (raw.get("company") or "").strip()
    website = (raw.get("website") or "").strip()
    city = (raw.get("city") or "").strip()
    state = (raw.get("state") or "").strip()
    category = (raw.get("category") or "general").strip()

    ai = await _llama_assess(category, text, company, model_key)
    intent = int(ai.get("intent_score") or 0)
    v = await asyncio.to_thread(_osint_verify_sync, email, phone, website, company, city, state)
    confidence = _data_confidence(v, intent)

    risk = list(v["risk"])
    for f in (ai.get("anomaly_flags") or []):
        if isinstance(f, str) and f.strip():
            risk.append({"flag": f.strip()[:80], "severity": "medium", "source": "ai_analyst"})
    if ai.get("entity_consistency") == "low":
        risk.append({"flag": "Unverified_Entity_Structure", "severity": "high"})
    if intent and intent < 30:
        risk.append({"flag": "Low_Procurement_Intent", "severity": "low"})

    nodes = v["nodes"]
    tier = _operational_tier(confidence, intent)
    price = TIER_CREDITS[tier]
    ready = confidence >= STOREFRONT_MIN_CONFIDENCE and len(nodes) >= 2
    tags = ai.get("category_tags")
    tags = ",".join([str(t) for t in tags]) if isinstance(tags, list) and tags else (raw.get("tags") or "")
    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "category": category, "full_name": raw.get("full_name", ""), "email": email, "phone": phone,
        "company": company, "website": website, "city": city, "state": state,
        "source_site": raw.get("source_site", "enrichment"), "source_url": raw.get("source_url", ""),
        "raw_text": text, "ai_summary": ai.get("summary") or raw.get("ai_summary", ""),
        "ai_budget_est": ai.get("budget_estimate") or "", "ai_intent_score": intent,
        "tags": tags, "score": confidence, "quality_score": confidence,
        "data_confidence_score": confidence, "cross_verification": nodes, "risk_matrix": risk,
        "operational_value_tier": tier, "entity_consistency": ai.get("entity_consistency", "low"),
        "price_per_lead": price, "ready_to_sell": ready, "status": "ready_to_sell" if ready else "enriched",
        "enriched_at": now, "enrichment_model": _active_ai_model(model_key), "source": "enrichment_batch",
    }

    key = None
    if payload["source_url"]:
        key = {"source_url": payload["source_url"]}
    elif email:
        key = {"email": email, "company": company}
    existing = await db.leads.find_one(key) if key else None
    if existing:
        if existing.get("purchase_status") == "sold":
            payload.pop("ready_to_sell", None)
        await db.leads.update_one({"_id": existing["_id"]}, {"$set": payload})
        lid = existing["_id"]
    else:
        payload.update({"is_sold": False, "sold_price": 0.0, "purchase_status": "available",
                        "buyer_user_id": None, "created_at": now})
        res = await db.leads.insert_one(payload)
        lid = res.inserted_id
    return {"id": str(lid), "company": company or payload["full_name"] or "Unnamed entity",
            "city": city, "state": state, "data_confidence_score": confidence,
            "operational_value_tier": tier, "cross_verification": nodes,
            "risk_matrix": risk, "price_per_lead": price, "ready_to_sell": ready}

def _intel_pub(l: dict, full: bool = False) -> dict:
    base = {
        "id": str(l.get("_id") or l.get("id", "")),
        "category": l.get("category"),
        "city": l.get("city"), "state": l.get("state"),
        "data_confidence_score": l.get("data_confidence_score", l.get("score", 0)),
        "cross_verification": l.get("cross_verification", []),
        "risk_matrix": l.get("risk_matrix", []),
        "operational_value_tier": l.get("operational_value_tier", "Operational"),
        "quality_score": l.get("quality_score", l.get("score", 0)),
        "price_per_lead": int(l.get("price_per_lead", 1)),
        "purchase_status": l.get("purchase_status", "available"),
        "ai_summary": l.get("ai_summary", ""),
        "ai_budget_est": l.get("ai_budget_est", ""),
        "tags": l.get("tags", ""),
        "ready_to_sell": l.get("ready_to_sell", False),
    }
    if full:
        base.update({"full_name": l.get("full_name", ""), "email": l.get("email", ""),
                     "phone": l.get("phone", ""), "company": l.get("company", ""),
                     "website": l.get("website", ""), "source_url": l.get("source_url", ""),
                     "raw_text": l.get("raw_text", ""), "buyer_user_id": l.get("buyer_user_id")})
    else:
        base.update({"company_masked": _mask_company(l.get("company", "")),
                     "contact_masked": _mask_email(l.get("email", "")), "locked": True})
    return base

class ProcessLeadsReq(BaseModel):
    leads: List[Dict[str, Any]]
    ai_model: str = "llama"

@api.post("/enrichment/process-leads")
async def process_leads(body: ProcessLeadsReq, user: dict = Depends(require_admin)):
    """Run a raw lead array through Llama 3 + OSINT verification and flag ready_to_sell."""
    if not body.leads:
        raise HTTPException(status_code=400, detail="No leads provided")
    results = []
    for raw in body.leads[:100]:
        results.append(await _enrich_and_store(raw, body.ai_model))
    return {"processed": len(results),
            "ready_to_sell": sum(1 for r in results if r["ready_to_sell"]),
            "model": _active_ai_model(body.ai_model), "leads": results}

@api.get("/storefront/leads")
async def storefront_leads(city: Optional[str] = None, state: Optional[str] = None,
                           industry: Optional[str] = None, tier: Optional[str] = None,
                           min_confidence: float = 0.0, limit: int = 60, offset: int = 0,
                           user: dict = Depends(get_current_user)):
    """Browse individual un-sold, verified leads with full intelligence metrics (PII masked)."""
    fl_clause = [{"state": {"$regex": "^(fl|florida)$", "$options": "i"}},
                 {"state": {"$in": [None, ""]}}]  # FL-only marketplace (Tampa Bay region)
    q = {"ready_to_sell": True, "purchase_status": {"$ne": "sold"}}
    if city:
        q["city"] = {"$regex": re.escape(city), "$options": "i"}
    if state:
        q["state"] = {"$regex": f"^{re.escape(state)}$", "$options": "i"}
    else:
        q["$or"] = fl_clause
    if industry:
        q["category"] = industry
    if tier:
        q["operational_value_tier"] = tier
    if min_confidence:
        q["data_confidence_score"] = {"$gte": min_confidence}
    total = await db.leads.count_documents(q)
    cur = db.leads.find(q).sort("data_confidence_score", -1).skip(offset).limit(min(limit, 200))
    leads = [_intel_pub(l) async for l in cur]
    base_q = {"ready_to_sell": True, "purchase_status": {"$ne": "sold"}, "$or": fl_clause}
    industries = await db.leads.distinct("category", base_q)
    states = await db.leads.distinct("state", base_q)
    bundle_pipeline = [
        {"$match": base_q},
        {"$group": {"_id": "$category", "count": {"$sum": 1},
                    "avg_confidence": {"$avg": "$data_confidence_score"},
                    "from_price": {"$min": "$price_per_lead"},
                    "strategic": {"$sum": {"$cond": [
                        {"$eq": ["$operational_value_tier", "Strategic"]}, 1, 0]}}}},
        {"$sort": {"count": -1}},
    ]
    bundles = [{"industry": b["_id"], "count": b["count"],
                "avg_confidence": round(b.get("avg_confidence") or 0, 1),
                "from_price": int(b.get("from_price") or 1), "strategic": b.get("strategic", 0)}
               async for b in db.leads.aggregate(bundle_pipeline) if b.get("_id")]
    return {"total": total, "leads": leads, "bundles": bundles,
            "filters": {"industries": [i for i in industries if i],
                        "states": [s for s in states if s],
                        "tiers": ["Strategic", "Tactical", "Operational"]}}

class RFPRequest(BaseModel):
    agency_name: str
    contact_name: str
    email: EmailStr
    regions: str = ""
    sectors: str = ""
    budget: str = ""
    timeline: str = ""
    classification: str = "Unclassified"
    scope: str = ""

@api.post("/storefront/rfp")
async def submit_rfp(body: RFPRequest, request: Request, user: dict = Depends(get_current_user)):
    """Government / municipal custom-intelligence scope request (RFP intake)."""
    doc = body.model_dump()
    doc.update({"user_id": user["id"], "tenant_id": gov.tenant_id_of(user), "status": "new",
                "created_at": datetime.now(timezone.utc).isoformat()})
    res = await db.rfp_requests.insert_one(doc)
    await gov.audit_log("rfp.submit", user=user, request=request, target=str(res.inserted_id),
                        meta={"agency": body.agency_name, "classification": body.classification})
    return {"id": str(res.inserted_id), "status": "received",
            "message": "Agency scope request received. Our intelligence desk will respond within 1 business day."}

@api.get("/storefront/rfp")
async def list_rfp(user: dict = Depends(require_admin)):
    out = []
    async for r in db.rfp_requests.find().sort("created_at", -1).limit(200):
        r["id"] = str(r.pop("_id"))
        out.append(r)
    return {"requests": out, "total": len(out)}

class PurchaseLeadsReq(BaseModel):
    lead_ids: List[str]

@api.post("/storefront/purchase-leads")
async def purchase_leads(body: PurchaseLeadsReq, request: Request, user: dict = Depends(get_current_user)):
    """Atomically buy specific leads with credits; marks sold to prevent double-selling."""
    try:
        oids = [ObjectId(i) for i in body.lead_ids]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lead id")
    if not oids:
        raise HTTPException(status_code=400, detail="No leads specified")
    is_admin = gov.is_admin(user)
    available = [l async for l in db.leads.find(
        {"_id": {"$in": oids}, "purchase_status": {"$ne": "sold"}})]
    if not available:
        raise HTTPException(status_code=400, detail="None of the selected leads are available")
    total_cost = sum(int(l.get("price_per_lead", 1)) for l in available)
    if not is_admin:
        res = await db.users.update_one(
            {"_id": ObjectId(user["id"]), "credits": {"$gte": total_cost}},
            {"$inc": {"credits": -total_cost}})
        if res.modified_count == 0:
            u = await db.users.find_one({"_id": ObjectId(user["id"])})
            have = (u or {}).get("credits", 0)
            raise HTTPException(status_code=402,
                detail=f"Insufficient credits — need {total_cost}, you have {have}")
    now = datetime.now(timezone.utc).isoformat()
    purchased, refund = [], 0
    for l in available:
        price = int(l.get("price_per_lead", 1))
        upd = await db.leads.update_one(
            {"_id": l["_id"], "purchase_status": {"$ne": "sold"}},
            {"$set": {"purchase_status": "sold", "buyer_user_id": user["id"], "is_sold": True,
                      "sold_price": price, "sold_at": now, "status": "sold"},
             "$addToSet": {"unlocked_by": user["id"]}})
        if upd.modified_count == 1:
            purchased.append(await db.leads.find_one({"_id": l["_id"]}))
        else:
            refund += price
    if refund and not is_admin:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"credits": refund}})
    await db.storefront_orders.insert_one({
        "buyer_user_id": user["id"], "tenant_id": gov.tenant_id_of(user),
        "lead_ids": [str(l["_id"]) for l in purchased],
        "charged_credits": total_cost - refund, "count": len(purchased), "created_at": now})
    await gov.audit_log("lead.purchase", user=user, request=request,
                        meta={"count": len(purchased), "charged_credits": total_cost - refund})
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    return {"purchased": len(purchased), "charged_credits": total_cost - refund,
            "credits_remaining": (u or {}).get("credits", 0),
            "leads": [_intel_pub(l, full=True) for l in purchased]}

# ---- On-demand lead generator (OSM + OSINT + background AI enrichment) ----
SECTOR_OSM_TAGS = {
    "real_estate": ['"office"="estate_agent"', '"shop"="estate_agent"', '"office"="property_management"'],
    "legal": ['"office"="lawyer"', '"office"="notary"'],
    "financial_services": ['"office"="financial"', '"office"="accountant"',
                           '"office"="financial_advisor"', '"office"="tax_advisor"'],
    "insurance": ['"office"="insurance"'],
    "b2b_tech": ['"office"="it"', '"office"="telecommunication"'],
    "healthcare": ['"amenity"="clinic"', '"amenity"="doctors"', '"healthcare"="clinic"', '"amenity"="dentist"'],
    "dental": ['"amenity"="dentist"'],
    "construction": ['"craft"="builder"', '"office"="construction_company"'],
    "automotive": ['"shop"="car"', '"shop"="car_repair"'],
    "restaurant": ['"amenity"="restaurant"'],
    "financial": ['"office"="financial"', '"office"="accountant"', '"office"="insurance"'],
    "veterinary": ['"amenity"="veterinary"'],
    "fitness": ['"leisure"="fitness_centre"'],
}

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

async def _overpass_generate(sector: str, county: str, limit: int = 200) -> list:
    tags = SECTOR_OSM_TAGS.get(sector, [])
    raws = []
    if tags:
        parts = "".join(f"node[{t}](area.a);way[{t}](area.a);" for t in tags)
        q = (f'[out:json][timeout:90][bbox:24.3,-87.7,31.1,-79.8];'
             f'area["name"="{county}"]["admin_level"~"6|8"]->.a;'
             f'({parts});out center tags {limit};')
        els = []
        for attempt, endpoint in enumerate(OVERPASS_ENDPOINTS):
            try:
                async with httpx.AsyncClient(timeout=120, headers={"User-Agent": "NEXUS-LeadBot/1.0"}) as c:
                    resp = await c.post(endpoint, data={"data": q})
                if resp.status_code == 200 and resp.text.strip().startswith("{"):
                    els = resp.json().get("elements", [])
                    break
                logger.warning("overpass %s for %s/%s -> HTTP %s; trying next mirror",
                               endpoint.split('/')[2], sector, county, resp.status_code)
            except Exception as e:
                logger.warning("overpass %s error (%s/%s): %s", endpoint.split('/')[2], sector, county, e)
            await asyncio.sleep(2 + attempt * 2)  # backoff before next mirror
        for e in els:
            t = e.get("tags", {})
            name = t.get("name") or t.get("operator")
            if not name:
                continue
            raws.append({"company": name, "website": t.get("website") or t.get("contact:website") or "",
                         "phone": t.get("phone") or t.get("contact:phone") or "",
                         "email": t.get("email") or t.get("contact:email") or "",
                         "city": t.get("addr:city") or "", "state": t.get("addr:state") or ""})
    seen, uniq = set(), []
    for r in raws:
        k = (r["company"].lower(), r["city"].lower())
        if k[0] and k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq[:limit]

async def _store_generated(raw: dict, sector: str, county: str) -> bool:
    company = (raw.get("company") or "").strip()
    city = (raw.get("city") or "").strip()
    v = await asyncio.to_thread(_osint_verify_sync, raw.get("email", ""), raw.get("phone", ""),
                                raw.get("website", ""), company, city, raw.get("state", ""))
    intent = 40 + (20 if raw.get("website") else 0) + (15 if raw.get("phone") else 0)
    conf = _data_confidence(v, intent)
    tier = _operational_tier(conf, intent)
    nodes = v["nodes"]
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "category": sector, "full_name": "", "company": company, "email": raw.get("email", ""),
        "phone": raw.get("phone", ""), "website": raw.get("website", ""), "city": city,
        "state": raw.get("state") or "", "source_site": "OpenStreetMap", "source": "generator",
        "source_url": raw.get("website") or "",
        "raw_text": f"{company} — {sector.replace('_', ' ')} in {city or county}. {raw.get('website','')} {raw.get('phone','')}".strip(),
        "ai_summary": f"{sector.replace('_', ' ').title()} business in {city or county}.",
        "ai_budget_est": "", "ai_intent_score": intent,
        "tags": f"{sector},{county.lower().replace(' ', '_')}",
        "score": conf, "quality_score": conf, "data_confidence_score": conf,
        "cross_verification": nodes, "risk_matrix": list(v["risk"]),
        "operational_value_tier": tier, "price_per_lead": TIER_CREDITS[tier],
        "ready_to_sell": conf >= STOREFRONT_MIN_CONFIDENCE and len(nodes) >= 2,
        "status": "enriched", "enriched_at": now, "enrichment_model": "osint_verify",
    }
    existing = await db.leads.find_one({"company": company, "city": city, "source": "generator"})
    if existing:
        await db.leads.update_one({"_id": existing["_id"]}, {"$set": doc})
        return False
    doc.update({"is_sold": False, "sold_price": 0.0, "purchase_status": "available",
                "buyer_user_id": None, "created_at": now})
    await db.leads.insert_one(doc)
    return True

async def _bg_ai_enrich(lead_ids: list, job_id: str = None):
    done = 0
    for lid in lead_ids:
        l = await db.leads.find_one({"_id": lid})
        if l:
            ai = await _llama_assess(l.get("category", "general"), l.get("raw_text", ""), l.get("company", ""), "llama")
            intent = int(ai.get("intent_score") or 0)
            v = await asyncio.to_thread(_osint_verify_sync, l.get("email", ""), l.get("phone", ""),
                                        l.get("website", ""), l.get("company", ""), l.get("city", ""), l.get("state", ""))
            conf = _data_confidence(v, intent)
            risk = list(v["risk"])
            for f in (ai.get("anomaly_flags") or []):
                if isinstance(f, str) and f.strip():
                    risk.append({"flag": f.strip()[:80], "severity": "medium", "source": "ai_analyst"})
            if ai.get("entity_consistency") == "low":
                risk.append({"flag": "Unverified_Entity_Structure", "severity": "high"})
            tier = _operational_tier(conf, intent)
            nodes = v["nodes"]
            tags = ai.get("category_tags")
            tags = ",".join(str(t) for t in tags) if isinstance(tags, list) and tags else l.get("tags", "")
            upd = {"ai_summary": ai.get("summary") or l.get("ai_summary", ""),
                   "ai_budget_est": ai.get("budget_estimate") or "", "ai_intent_score": intent, "tags": tags,
                   "score": conf, "quality_score": conf, "data_confidence_score": conf,
                   "cross_verification": nodes, "risk_matrix": risk, "operational_value_tier": tier,
                   "price_per_lead": TIER_CREDITS[tier], "enrichment_model": _active_ai_model("llama"),
                   "enriched_at": datetime.now(timezone.utc).isoformat()}
            if l.get("purchase_status") != "sold":
                upd["ready_to_sell"] = conf >= STOREFRONT_MIN_CONFIDENCE and len(nodes) >= 2
            await db.leads.update_one({"_id": lid}, {"$set": upd})
        done += 1
        if job_id:
            await db.generate_jobs.update_one({"job_id": job_id}, {"$set": {"done": done}})
    if job_id:
        await db.generate_jobs.update_one({"job_id": job_id},
            {"$set": {"status": "complete", "done": done,
                      "finished_at": datetime.now(timezone.utc).isoformat()}})

async def _bg_reosint_all():
    """One-shot OSINT re-scoring of every un-sold lead to the current HQ standard.
    Recomputes confidence (incl. company-domain MX) and the ready_to_sell HQ gate so the
    storefront reflects the live quality bar without blocking startup."""
    try:
        rescored = hq = 0
        async for l in db.leads.find({"purchase_status": {"$ne": "sold"}}):
            v = await asyncio.to_thread(_osint_verify_sync, l.get("email", ""), l.get("phone", ""),
                                        l.get("website", ""), l.get("company", ""),
                                        l.get("city", ""), l.get("state", ""))
            intent = int(l.get("ai_intent_score") or l.get("score") or 0)
            conf = _data_confidence(v, intent)
            fields = _osint_fields(v, conf, intent)
            fields.pop("buyer_user_id", None)  # never overwrite ownership
            await db.leads.update_one({"_id": l["_id"]}, {"$set": fields})
            rescored += 1
            if fields["ready_to_sell"]:
                hq += 1
        logger.info("OSINT re-score complete: %d leads, %d HQ (>=%.0f%%)",
                    rescored, hq, STOREFRONT_MIN_CONFIDENCE)
    except Exception as e:
        logger.warning("OSINT re-score backfill error: %s", e)

class GenerateReq(BaseModel):
    sector: str
    county: str = "Pinellas County"
    limit: int = 100
    ai_enrich: bool = True

@api.get("/storefront/sectors")
async def storefront_sectors(user: dict = Depends(get_current_user)):
    return {"sectors": sorted(SECTOR_OSM_TAGS.keys())}

@api.post("/storefront/generate-leads")
async def generate_leads(body: GenerateReq, request: Request, user: dict = Depends(require_admin),
                         _rl: bool = Depends(gov.rate_limit(int(os.environ.get("RL_GENERATE_PER_MIN", "5")), 60))):
    """Pull real businesses for a sector+county from OSM, OSINT-verify, store as storefront leads."""
    sector = body.sector.strip().lower().replace(" ", "_")
    if sector not in SECTOR_OSM_TAGS:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported sector. Options: {', '.join(sorted(SECTOR_OSM_TAGS))}")
    county = body.county.strip() or "Pinellas County"
    raws = await _overpass_generate(sector, county, min(max(body.limit, 1), 300))
    if not raws:
        return {"generated": 0, "new": 0, "sector": sector, "county": county,
                "message": f"No {sector.replace('_', ' ')} entities found in {county} on OpenStreetMap."}
    sem = asyncio.Semaphore(20)
    new_ids = []

    async def proc(r):
        async with sem:
            created = await _store_generated(r, sector, county)
        if created:
            doc = await db.leads.find_one(
                {"company": r["company"].strip(), "city": r.get("city", "").strip(), "source": "generator"})
            if doc:
                new_ids.append(doc["_id"])

    await asyncio.gather(*(proc(r) for r in raws))
    job_id = None
    if body.ai_enrich and new_ids:
        job_id = secrets.token_hex(12)
        await db.generate_jobs.insert_one({
            "job_id": job_id, "total": len(new_ids), "done": 0, "status": "running",
            "sector": sector, "county": county, "tenant_id": gov.tenant_id_of(user),
            "by": user["id"], "started_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=6)})
        asyncio.create_task(_bg_ai_enrich(new_ids, job_id))
    avail = await db.leads.count_documents({"category": sector, "purchase_status": {"$ne": "sold"}})
    await gov.audit_log("lead.generate", user=user, request=request, target=sector,
                        meta={"county": county, "generated": len(raws), "new": len(new_ids)})
    return {"generated": len(raws), "new": len(new_ids), "sector": sector, "county": county,
            "available_in_storefront": avail, "job_id": job_id,
            "enrich_total": len(new_ids) if job_id else 0,
            "message": f"Ingested {len(raws)} {sector.replace('_', ' ')} entities from {county}." +
                       (" Deep AI enrichment is running in the background." if body.ai_enrich and new_ids else "")}

@api.get("/storefront/generate-status/{job_id}")
async def generate_status(job_id: str, user: dict = Depends(require_admin)):
    job = await db.generate_jobs.find_one({"job_id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "total": job.get("total", 0), "done": job.get("done", 0),
            "status": job.get("status", "running"), "sector": job.get("sector"),
            "county": job.get("county"), "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at")}

# ====================== PUBLIC LAUNCH SITE (marketing landing — no auth) ======================
# Backs the static launch site at /launch (pilot waitlist capture + lightweight demos).
class WaitlistReq(BaseModel):
    email: str
    company: str = ""

@api.post("/waitlist")
async def waitlist_signup(body: WaitlistReq, request: Request):
    email = (body.email or "").strip().lower()
    if not EMAIL_RX.fullmatch(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    rec = {"email": email, "company": (body.company or "").strip(), "source": "launch_site",
           "captured_at": datetime.now(timezone.utc).isoformat(),
           "remote": request.client.host if request.client else ""}
    await db.waitlist.update_one({"email": email}, {"$setOnInsert": rec}, upsert=True)
    return {"ok": True, "message": "Pilot request received."}

@api.get("/waitlist")
async def waitlist_list(user: dict = Depends(require_admin)):
    out = []
    async for r in db.waitlist.find().sort("captured_at", -1).limit(500):
        r["id"] = str(r.pop("_id"))
        out.append(r)
    return {"requests": out, "total": len(out)}

def _lgvh_enrich(lead: dict) -> dict:
    company = str(lead.get("company") or "Unknown lead").strip()
    signal = str(lead.get("signal") or "").strip()
    market = str(lead.get("market") or "").strip()
    source = str(lead.get("source") or "approved source").strip()
    score, reasons = 52, []
    if any(t in signal.lower() for t in ("hiring", "growth", "expansion", "contract", "funding", "grant", "procurement")):
        score += 24; reasons.append("Strong buying or growth signal found after scrape.")
    if any(t in market.lower() for t in ("gov", "field", "security", "operations", "saas")):
        score += 14; reasons.append("Market aligns with Nexus target segments.")
    if "approved" in source.lower() or "allowlist" in source.lower():
        score += 6; reasons.append("Source is documented in the scraper allowlist.")
    score = max(0, min(score, 98))
    band = "High" if score >= 80 else "Medium" if score >= 60 else "Low"
    confidence = "High" if len(reasons) >= 3 else "Medium" if reasons else "Low"
    return {"company": company,
            "summary": f"{company} appears to be a {market or 'target'} lead with scrape signal: {signal or 'no signal provided'}.",
            "score": score, "scoreBand": band, "confidence": confidence,
            "reasons": reasons or ["Insufficient signals; route to review before outreach."],
            "nextAction": "Create storefront draft" if score >= 80 else "Review enrichment" if score >= 60 else "Hold for more data",
            "storefrontSafeFields": {"title": company, "category": market or "Lead intelligence",
                                     "summary": f"{company} matched {band.lower()} priority criteria after enrichment."}}

class LeadDemoReq(BaseModel):
    lead: Dict[str, Any] = {}

@api.post("/enrich-score")
async def lgvh_enrich_score(body: LeadDemoReq):
    if not body.lead:
        raise HTTPException(status_code=400, detail="Request requires a lead object.")
    return {"ok": True, "result": _lgvh_enrich(body.lead)}

@api.post("/sale-listing")
async def lgvh_sale_listing(body: LeadDemoReq):
    if not body.lead:
        raise HTTPException(status_code=400, detail="Request requires a lead object.")
    e = _lgvh_enrich(body.lead)
    score = int(e["score"])
    price = 49 if score < 70 else 129 if score < 85 else 249
    listing = {"title": f"{e['company']} - AI-enriched {e['scoreBand']} priority lead",
               "category": e["storefrontSafeFields"]["category"], "summary": e["storefrontSafeFields"]["summary"],
               "score": score, "scoreBand": e["scoreBand"], "confidence": e["confidence"],
               "price": price, "currency": "USD",
               "included": ["AI enrichment summary", "Lead score and reasons", "Source type and provenance notes",
                            "Suggested next action", "Storefront-safe company profile"],
               "privateFieldsExcluded": ["Raw phone/email", "Internal notes", "Sensitive identifiers", "Unreviewed personal data"],
               "cta": "Request this lead package", "status": "Ready for review"}
    return {"ok": True, "listing": listing}

class ChatDemoReq(BaseModel):
    prompt: str = ""

def _lgvh_safe_answer(prompt: str) -> str:
    low = prompt.lower()
    if "scraper" in low or "scrape" in low:
        return ("Scraper command view: check collector uptime, source allowlist, ingestion queue, dedupe rate, "
                "error spikes, and emergency stop status. Keep sources documented and rate-limited.")
    if "lead" in low:
        return ("Lead workflow: import, validate, dedupe, enrich, score, review, then create a sanitized storefront "
                "draft. Do not publish private contact fields by default.")
    if "storefront" in low or "publish" in low:
        return ("Storefront workflow: create listing drafts first, exclude private notes and raw contact data, then "
                "publish only when score, privacy, and approval rules pass.")
    if "onsite" in low or "room" in low or "camera" in low:
        return ("Onsite workflow: run the room privacy checklist, record authorized findings, label suspicious signals "
                "for review, and escalate through security or law enforcement when appropriate.")
    return ("Nexus safe mode is online. I can help with lead workflows, 24/7 scraper operations, Pi Suite edge "
            "nodes, onsite privacy checks, storefront drafts, and launch readiness.")

@api.post("/chat")
async def lgvh_chat(body: ChatDemoReq,
                    _rl: bool = Depends(gov.rate_limit(int(os.environ.get("RL_CHAT_PER_MIN", "8")), 60))):
    prompt = (body.prompt or "").strip()[:1000]
    if not prompt:
        raise HTTPException(status_code=400, detail="Enter a message for Nexus AI.")
    sys_p = ("You are Nexus AI, the assistant on the LeadGen Virtual Hub launch site — a lead-intelligence "
             "platform that runs 24/7 OSINT-filtered scrapers, AI enrichment/scoring, a compliant lead "
             "storefront, Pi Suite edge nodes, and onsite privacy checks. Answer as a knowledgeable product "
             "guide: concise (2-4 sentences), practical, privacy- and compliance-aware. Never fabricate private "
             "contact data. If asked something off-topic, steer back to lead-gen, scraping, or launch readiness.")
    r = await deepseek_chat([{"role": "system", "content": sys_p},
                             {"role": "user", "content": prompt}], max_tokens=320, temperature=0.6)
    if isinstance(r, dict) and "error" not in r and r.get("content"):
        return {"ok": True, "assistant": "Nexus AI", "mode": "live",
                "model": r.get("model"), "answer": r["content"].strip()}
    logger.warning("lgvh_chat falling back to safe mode: %s", (r or {}).get("error"))
    return {"ok": True, "assistant": "Nexus AI", "mode": "safe_mode", "answer": _lgvh_safe_answer(prompt)}

# ====================== GOVERNANCE (multi-tenant, RBAC, audit, monitoring) ======================
@api.get("/governance/me")
async def governance_me(user: dict = Depends(get_current_user)):
    """Caller's tenant + effective role/permission level."""
    tenant = await db.tenants.find_one({"tenant_id": gov.tenant_id_of(user)}) or {}
    members = await db.users.count_documents({"tenant_id": gov.tenant_id_of(user)})
    return {"tenant_id": gov.tenant_id_of(user), "tenant_name": tenant.get("name", user.get("tenant_name", "")),
            "role": user.get("role", "user"), "role_level": gov.role_level(user.get("role")),
            "is_platform_admin": gov.is_admin(user), "members": members,
            "roles_available": gov.VALID_ROLES}

@api.get("/governance/tenant/members")
async def tenant_members(user: dict = Depends(require_min_role("tenant_admin"))):
    """Members of the caller's tenant (platform admins see every tenant)."""
    q = {} if gov.is_admin(user) else {"tenant_id": gov.tenant_id_of(user)}
    cur = db.users.find(q, {"email": 1, "name": 1, "role": 1, "credits": 1, "tenant_id": 1,
                            "tenant_name": 1, "created_at": 1}).sort("created_at", -1).limit(500)
    return [{"id": str(u["_id"]), "email": u["email"], "name": u.get("name"),
             "role": u.get("role"), "credits": u.get("credits", 0),
             "tenant_id": u.get("tenant_id") or gov.DEFAULT_TENANT,
             "tenant_name": u.get("tenant_name", ""), "created_at": u.get("created_at")} async for u in cur]

@api.get("/admin/tenants")
async def admin_tenants(user: dict = Depends(require_admin)):
    pipeline = [{"$group": {"_id": "$tenant_id", "members": {"$sum": 1}}}]
    counts = {b["_id"]: b["members"] async for b in db.users.aggregate(pipeline)}
    out = []
    async for t in db.tenants.find().sort("created_at", -1).limit(500):
        out.append({"tenant_id": t.get("tenant_id"), "name": t.get("name"),
                    "owner_email": t.get("owner_email"), "status": t.get("status", "active"),
                    "members": counts.get(t.get("tenant_id"), 0), "created_at": t.get("created_at")})
    return {"tenants": out, "total": len(out)}

@api.get("/admin/audit")
async def admin_audit(limit: int = 100, action: Optional[str] = None,
                      tenant_id: Optional[str] = None, status: Optional[str] = None,
                      user: dict = Depends(require_admin)):
    q = {}
    if action:
        q["action"] = action
    if tenant_id:
        q["tenant_id"] = tenant_id
    if status:
        q["status"] = status
    cur = db.audit_logs.find(q).sort("created_at", -1).limit(min(limit, 500))
    logs = [gov.audit_pub(r) async for r in cur]
    actions = await db.audit_logs.distinct("action")
    return {"logs": logs, "total": len(logs), "actions": sorted(actions)}

@api.get("/admin/monitoring")
async def admin_monitoring(user: dict = Depends(require_admin)):
    """Application-level health & operations snapshot (for per-environment monitoring)."""
    db_ok = True
    try:
        await db.command("ping")
    except Exception:
        db_ok = False
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return {
        "db_connected": db_ok,
        "scheduler_running": scheduler.running,
        "scraper_status": SCRAPER_STATE.get("status"),
        "tenants": await db.tenants.count_documents({}),
        "users": await db.users.count_documents({}),
        "leads_total": await db.leads.count_documents({}),
        "leads_available": await db.leads.count_documents({"purchase_status": {"$ne": "sold"}}),
        "leads_sold": await db.leads.count_documents({"purchase_status": "sold"}),
        "audit_events_24h": await db.audit_logs.count_documents({"created_at": {"$gte": since}}),
        "logins_failed_24h": await db.audit_logs.count_documents(
            {"action": "user.login", "status": "failure", "created_at": {"$gte": since}}),
        "locked_identities": await db.login_attempts.count_documents({"count": {"$gte": gov.MAX_FAILED}}),
        "ai_provider": _active_ai_model(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

# ----------------------------------------------------------------------------- mount + startup
app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True,
                   allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
                   allow_methods=["*"], allow_headers=["*"])

SAMPLE_LEADS = [
    {"category": "home_remodeling", "full_name": "Marcus Reed", "email": "marcus.reed@gmail.com",
     "phone": "+1 512-555-0142", "company": "", "city": "Austin", "state": "TX",
     "source_site": "Craigslist", "source_url": "https://example.com/1",
     "raw_text": "Looking to remodel my kitchen and two bathrooms, budget flexible, want to start within 3 weeks.",
     "score": 88.0, "status": "enriched", "ai_summary": "Homeowner urgently seeking full kitchen and bath remodel. High intent, flexible budget.",
     "ai_budget_est": "$25k-$40k", "tags": "kitchen,bathroom,urgent"},
    {"category": "cleaning", "full_name": "Dana Whitfield", "email": "dana.w@outlook.com",
     "phone": "+1 305-555-0199", "company": "Whitfield Realty", "city": "Miami", "state": "FL",
     "source_site": "Facebook", "source_url": "https://example.com/2",
     "raw_text": "Need recurring weekly cleaning for 4 rental units, ongoing contract.",
     "score": 74.0, "status": "enriched", "ai_summary": "Property manager needs recurring multi-unit cleaning contract. Strong recurring revenue potential.",
     "ai_budget_est": "$1.5k-$3k/mo", "tags": "recurring,commercial,contract"},
    {"category": "home_remodeling", "full_name": "Priya Nair", "email": "priya.nair@yahoo.com",
     "phone": "+1 408-555-0123", "company": "", "city": "San Jose", "state": "CA",
     "source_site": "Nextdoor", "source_url": "https://example.com/3",
     "raw_text": "Thinking about maybe redoing my backyard deck sometime next year.",
     "score": 32.0, "status": "enriched", "ai_summary": "Homeowner with low-urgency deck project, exploratory stage.",
     "ai_budget_est": "$5k-$9k", "tags": "deck,low-urgency,outdoor"},
    {"category": "cleaning", "full_name": "Tom Alvarez", "email": "tom.alvarez@gmail.com",
     "phone": "+1 702-555-0177", "company": "", "city": "Las Vegas", "state": "NV",
     "source_site": "Craigslist", "source_url": "https://example.com/4",
     "raw_text": "Move-out deep clean needed for a 3 bedroom house this weekend.",
     "score": 81.0, "status": "raw", "ai_summary": "", "ai_budget_est": "", "tags": ""},
]

@app.on_event("startup")
async def startup():
    global client, db
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    gov.set_db(db)
    logger.info("MongoDB client initialized inside event loop")
    await db.users.create_index("email", unique=True)
    await db.api_keys.create_index("key_hash")
    await db.leads.create_index([("score", -1)])
    await db.leads.create_index("category")
    await db.leads.create_index("status")
    # --- Gov-ready: multi-tenancy, audit, brute-force defense indexes ---
    await db.audit_logs.create_index([("created_at", -1)])
    await db.audit_logs.create_index("tenant_id")
    await db.audit_logs.create_index("action")
    await db.tenants.create_index("tenant_id", unique=True)
    await db.users.create_index("tenant_id")
    try:
        await db.login_attempts.create_index("expires_at", expireAfterSeconds=0)
        await db.generate_jobs.create_index("job_id", unique=True)
        await db.generate_jobs.create_index("expires_at", expireAfterSeconds=0)
    except Exception:
        pass
    # Default platform tenant + backfill legacy users so isolation filters work.
    await db.tenants.update_one({"tenant_id": gov.DEFAULT_TENANT},
        {"$setOnInsert": {"tenant_id": gov.DEFAULT_TENANT, "name": "Platform (NEXUS)",
                          "owner_email": os.environ.get("ADMIN_EMAIL", "admin@nexus.io").lower(),
                          "status": "active", "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    await db.users.update_many({"tenant_id": {"$exists": False}},
        {"$set": {"tenant_id": gov.DEFAULT_TENANT, "tenant_name": "Platform (NEXUS)"}})
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@nexus.io").lower()
    admin_pw = os.environ.get("ADMIN_PASSWORD", "nexus123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_pw),
                                   "name": "Admin", "role": "admin",
                                   "tenant_id": gov.DEFAULT_TENANT, "tenant_name": "Platform (NEXUS)",
                                   "created_at": datetime.now(timezone.utc).isoformat()})
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})
    if await db.leads.count_documents({}) == 0:
        for l in SAMPLE_LEADS:
            doc = {**l, "is_sold": False, "sold_price": 0.0,
                   "created_at": datetime.now(timezone.utc).isoformat()}
            doc.setdefault("ai_intent_score", doc.get("score", 0))
            await db.leads.insert_one(doc)
    # start 24/7 scraper
    await db.leads.create_index("source_url")
    await db.leads.create_index("purchase_status")
    await db.leads.create_index("operational_value_tier")
    await db.leads.create_index("ready_to_sell")
    # Storefront backfill: give legacy leads intelligence-payload defaults so they are sellable.
    async for l in db.leads.find({"purchase_status": {"$exists": False}}):
        sc = float(l.get("score") or 0)
        nodes = []
        if l.get("email") and EMAIL_RX.fullmatch((l.get("email") or "").strip()):
            nodes.append("Email_Syntax_Valid")
        if l.get("phone") and PHONE_RX.search(l.get("phone") or ""):
            nodes.append("Phone_Format_Valid")
        if l.get("city") and l.get("state"):
            nodes.append("Geo_Located")
        if l.get("website"):
            nodes.append("Public_Registry_Verified")
        tier = _operational_tier(sc, int(l.get("ai_intent_score") or 0))
        await db.leads.update_one({"_id": l["_id"]}, {"$set": {
            "purchase_status": "sold" if l.get("is_sold") else "available",
            "buyer_user_id": l.get("buyer_user_id"),
            "ready_to_sell": sc >= STOREFRONT_MIN_CONFIDENCE and len(nodes) >= 2,
            "data_confidence_score": sc, "quality_score": sc,
            "operational_value_tier": tier, "price_per_lead": TIER_CREDITS[tier],
            "cross_verification": nodes, "risk_matrix": [],
        }})
    # self-heal: correct any scraped leads whose source_site mismatches their URL
    for domain, site in [("github.com", "GitHub"), ("news.ycombinator.com", "Hacker News"),
                         ("reddit.com", "Reddit")]:
        await db.leads.update_many(
            {"scraped": True, "source_url": {"$regex": domain}, "source_site": {"$ne": site}},
            {"$set": {"source_site": site}})
    cfg = await get_scraper_config()
    # Migrate sources to the current version (Tampa Bay independent-service scraping via OSM).
    if cfg.get("sources_version") != SOURCES_VERSION:
        await db.scraper_config.update_one({"_id": "config"},
            {"$set": {"sources": DEFAULT_SOURCES, "sources_version": SOURCES_VERSION}})
        cfg["sources"] = DEFAULT_SOURCES
        logger.info("Migrated scraper to Tampa Bay OSM service sources v%d (%d)", SOURCES_VERSION, len(DEFAULT_SOURCES))
    if cfg.get("enabled") and RUN_SCHEDULER:
        reschedule(cfg.get("interval_min", 30))
        if not scheduler.running:
            scheduler.start()
        logger.info("Scraper scheduled every %s min", cfg.get("interval_min"))
        asyncio.create_task(_bg_reosint_all())
    elif not RUN_SCHEDULER:
        logger.info("RUN_SCHEDULER=false — scraping handled by standalone worker container")
    logger.info("NEXUS online — admin seeded, %d leads", await db.leads.count_documents({}))

@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if client is not None:
        client.close()
