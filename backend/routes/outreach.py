"""NEXUS outreach routes."""
from server import (
    AutoOutreachCfg,
    Depends,
    EnrichReq,
    HTTPException,
    OUTREACH_TEMPLATES,
    OutreachSendReq,
    Request,
    Response,
    SAMPLE_PACK,
    StreamingResponse,
    _auto_outreach_sweep,
    _is_fl_lead,
    _outreach_recipients,
    _personalize,
    _run_email_enrichment,
    _sample_pack_attachment,
    _sample_pack_csv,
    _sample_pack_pdf,
    api,
    asyncio,
    datetime,
    db,
    gov,
    os,
    require_admin,
    send_email,
    timezone,
)


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


@api.post("/outreach/auto/run")
async def run_auto_outreach(user: dict = Depends(require_admin)):
    return await _auto_outreach_sweep("manual-trigger")


@api.get("/outreach/templates")
async def outreach_templates(user: dict = Depends(require_admin)):
    return {"templates": [{"id": k, **v} for k, v in OUTREACH_TEMPLATES.items()]}


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
