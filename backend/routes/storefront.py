"""NEXUS storefront routes."""
from server import (
    Depends,
    GenerateReq,
    HTTPException,
    ObjectId,
    Optional,
    PurchaseLeadsReq,
    RFPRequest,
    Request,
    SECTOR_OSM_TAGS,
    _bg_ai_enrich,
    _intel_pub,
    _overpass_generate,
    _store_generated,
    api,
    asyncio,
    datetime,
    db,
    get_current_user,
    gov,
    os,
    re,
    require_admin,
    secrets,
    timedelta,
    timezone,
)


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
