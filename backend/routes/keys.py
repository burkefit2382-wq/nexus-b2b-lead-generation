"""NEXUS keys routes."""
from server import (
    ApiKeyCreate,
    Depends,
    ObjectId,
    Request,
    _key_pub,
    api,
    datetime,
    db,
    get_current_user,
    gov,
    hash_api_key,
    secrets,
    timezone,
)


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
