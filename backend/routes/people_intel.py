"""NEXUS people_intel routes."""
from server import (
    Depends,
    IdentityInput,
    PeopleScanReq,
    _ai_profile,
    _build_footprint,
    _public_records,
    _resolve_identity,
    api,
    datetime,
    db,
    get_current_user,
    gov,
    timezone,
)


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
