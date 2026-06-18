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
from typing import Optional, List

import jwt
import bcrypt
import httpx
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("nexus")

# ----------------------------------------------------------------------------- DB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

require_admin = require_role("admin")

# ----------------------------------------------------------------------------- DeepSeek (HF router)
def _hf_chat_sync(messages, max_tokens=600, temperature=0.4):
    token = os.environ.get("HF_TOKEN", "")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3.1:novita")
    base = os.environ.get("HF_ROUTER_BASE", "https://router.huggingface.co/v1")
    if not token:
        return {"error": "No HF_TOKEN configured"}
    try:
        from openai import OpenAI
        c = OpenAI(base_url=base, api_key=token)
        r = c.chat.completions.create(model=model, messages=messages,
                                      max_tokens=max_tokens, temperature=temperature)
        return {"content": r.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}

async def deepseek_chat(messages, **kw):
    return await asyncio.to_thread(_hf_chat_sync, messages, **kw)

# ----------------------------------------------------------------------------- App / routers
app = FastAPI(title="NEXUS OSINT Orchestrator", version="2.0.0")
api = APIRouter(prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "online", "version": "2.0.0", "system": "NEXUS"}

# ====================== AUTH ======================
class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = "Operator"

class LoginReq(BaseModel):
    email: EmailStr
    password: str

def _pub(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u.get("name", ""), "role": u.get("role", "user")}

@api.post("/auth/register")
async def register(body: RegisterReq, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {"email": email, "password_hash": hash_password(body.password),
           "name": body.name, "role": "user", "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    return _pub({"id": uid, **doc})

@api.post("/auth/login")
async def login(body: LoginReq, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    uid = str(user["_id"])
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
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
async def create_api_key(body: ApiKeyCreate, user: dict = Depends(get_current_user)):
    raw = "nxs_" + secrets.token_urlsafe(32)
    doc = {"user_id": user["id"], "name": body.name, "key_hash": hash_api_key(raw),
           "prefix": raw[:12], "created_at": datetime.now(timezone.utc).isoformat(),
           "last_used": None, "calls": 0, "revoked": False}
    res = await db.api_keys.insert_one(doc)
    # full key returned ONCE only
    return {"id": str(res.inserted_id), "name": body.name, "api_key": raw,
            "prefix": doc["prefix"], "warning": "Store this key now — it will not be shown again."}

@api.get("/keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    cur = db.api_keys.find({"user_id": user["id"]}).sort("created_at", -1)
    return [_key_pub(k) async for k in cur]

@api.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str, user: dict = Depends(get_current_user)):
    await db.api_keys.update_one({"_id": ObjectId(key_id), "user_id": user["id"]},
                                 {"$set": {"revoked": True}})
    return {"revoked": key_id}

# ====================== ADMIN (role-gated) ======================
@api.get("/admin/users")
async def admin_list_users(user: dict = Depends(require_admin)):
    cur = db.users.find({}).sort("created_at", -1).limit(200)
    return [{"id": str(u["_id"]), "email": u["email"], "name": u.get("name"),
             "role": u.get("role"), "created_at": u.get("created_at")} async for u in cur]

class RoleUpdate(BaseModel):
    role: str

@api.patch("/admin/users/{user_id}/role")
async def admin_set_role(user_id: str, body: RoleUpdate, user: dict = Depends(require_admin)):
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="role must be user or admin")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": body.role}})
    return {"updated": user_id, "role": body.role}

# ====================== LEADS ======================
def _lead_pub(l: dict) -> dict:
    l = dict(l)
    l["id"] = str(l.pop("_id"))
    return l

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
    leads = [_lead_pub(l) async for l in cur]
    return {"total": total, "leads": leads}

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
    async for l in db.leads.find(q).sort("score", -1).limit(5000):
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

async def _enrich_one(lead: dict) -> dict:
    txt = (lead.get("raw_text") or f"{lead.get('full_name','')} {lead.get('company','')} {lead.get('city','')}").strip()[:1500]
    prompt = ("Analyze this service lead. Return ONLY valid JSON with keys: "
              "summary (2 sentences), intent_score (0-100 integer), "
              "budget_estimate (string like '$2k-$5k'), urgency (low/medium/high/urgent), "
              "category_tags (list of 3 strings).\n\n"
              f"Category: {lead.get('category')} | Source: {lead.get('source_site')}\nContent: {txt}")
    r = await deepseek_chat([{"role": "user", "content": prompt}], max_tokens=350, temperature=0.2)
    if "error" in r:
        return r
    out = r["content"].strip()
    if "```" in out:
        out = out.split("```")[1].replace("json", "", 1).strip()
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
    return {"loaded": configured, "model": os.environ.get("DEEPSEEK_MODEL"),
            "provider": "Hugging Face Router", "status": "ready" if configured else "no_token"}

class ChatReq(BaseModel):
    message: str

@api.post("/enrichment/chat")
async def ai_chat(body: ChatReq, user: dict = Depends(get_current_user)):
    total = await db.leads.count_documents({})
    hot = await db.leads.count_documents({"score": {"$gte": 70}})
    sys_p = (f"You are NEXUS, an elite OSINT and lead-generation AI assistant. "
             f"System stats: {total} total leads, {hot} hot leads (score>=70). "
             "Help with lead analysis, OSINT intel, digital footprints and cybersecurity. Be concise.")
    r = await deepseek_chat([{"role": "system", "content": sys_p},
                             {"role": "user", "content": body.message}], max_tokens=500, temperature=0.7)
    if "error" in r:
        return {"error": r["error"]}
    return {"response": r["content"]}

# ====================== OSINT TOOLS (cloud-native) ======================
async def _save_report(target, tool, result):
    await db.osint_reports.insert_one({"target": target, "tool_used": tool,
                                       "result_json": json.dumps(result, default=str)[:5000],
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
    await _save_report(body.target, "ip_lookup", res)
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
    await _save_report(body.target, "dns", res)
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
    await _save_report(body.target, "phone", res)
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
    await _save_report(body.target, "social", res)
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
    await _save_report(body.target, "geolocate", res)
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
    await _save_report(body.target, "breach", res)
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
    await _save_report(body.target, "subdomains", res)
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
    await _save_report(body.target, "portscan", res)
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
    await _save_report(body.url, "metadata", res)
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
    await _save_report(body.dork, "dork", res)
    return res

@api.get("/osint/reports")
async def osint_reports(limit: int = 50, user: dict = Depends(get_current_user)):
    cur = db.osint_reports.find({}).sort("created_at", -1).limit(limit)
    return [{"id": str(r["_id"]), "target": r.get("target"), "tool": r.get("tool_used"),
             "created_at": r.get("created_at")} async for r in cur]

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
    await db.users.create_index("email", unique=True)
    await db.api_keys.create_index("key_hash")
    await db.leads.create_index([("score", -1)])
    await db.leads.create_index("category")
    await db.leads.create_index("status")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@nexus.io").lower()
    admin_pw = os.environ.get("ADMIN_PASSWORD", "nexus123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_pw),
                                   "name": "Admin", "role": "admin",
                                   "created_at": datetime.now(timezone.utc).isoformat()})
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})
    if await db.leads.count_documents({}) == 0:
        for l in SAMPLE_LEADS:
            doc = {**l, "is_sold": False, "sold_price": 0.0,
                   "created_at": datetime.now(timezone.utc).isoformat()}
            doc.setdefault("ai_intent_score", doc.get("score", 0))
            await db.leads.insert_one(doc)
    logger.info("NEXUS online — admin seeded, %d leads", await db.leads.count_documents({}))

@app.on_event("shutdown")
async def shutdown():
    client.close()
