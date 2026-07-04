"""NEXUS admin routes."""
from server import (
    Depends,
    HTTPException,
    ObjectId,
    Optional,
    Request,
    RoleUpdate,
    SCRAPER_STATE,
    _active_ai_model,
    api,
    datetime,
    db,
    get_current_user,
    gov,
    require_admin,
    require_min_role,
    scheduler,
    timedelta,
    timezone,
)


@api.get("/admin/users")
async def admin_list_users(user: dict = Depends(require_admin)):
    cur = db.users.find({}, {"email": 1, "name": 1, "role": 1, "credits": 1, "tenant_id": 1,
                             "tenant_name": 1, "created_at": 1}).sort("created_at", -1).limit(500)
    return [{"id": str(u["_id"]), "email": u["email"], "name": u.get("name"),
             "role": u.get("role"), "credits": u.get("credits", 0),
             "tenant_id": u.get("tenant_id") or gov.DEFAULT_TENANT,
             "tenant_name": u.get("tenant_name", ""),
             "created_at": u.get("created_at")} async for u in cur]


@api.patch("/admin/users/{user_id}/role")
async def admin_set_role(user_id: str, body: RoleUpdate, request: Request, user: dict = Depends(require_admin)):
    if body.role not in gov.VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(gov.VALID_ROLES)}")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": body.role}})
    await gov.audit_log("admin.set_role", user=user, request=request, target=user_id,
                        meta={"role": body.role})
    return {"updated": user_id, "role": body.role}


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
