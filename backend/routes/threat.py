"""NEXUS threat routes."""
from server import (
    Depends,
    HTTPException,
    ObjectId,
    OutreachProfile,
    Request,
    SendPitchReq,
    ThreatScanReq,
    _run_threat_scan,
    api,
    datetime,
    db,
    gov,
    os,
    require_admin,
    send_email,
    timezone,
)


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


@api.get("/threat/outreach-profile")
async def get_outreach_profile(user: dict = Depends(require_admin)):
    p = await db.outreach_profile.find_one({"_id": "profile"}) or {}
    p.pop("_id", None)
    return p


@api.put("/threat/outreach-profile")
async def set_outreach_profile(body: OutreachProfile, user: dict = Depends(require_admin)):
    await db.outreach_profile.update_one({"_id": "profile"}, {"$set": body.model_dump()}, upsert=True)
    return {"updated": True, **body.model_dump()}


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
