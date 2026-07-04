"""NEXUS enrichment routes."""
from server import (
    BusinessReq,
    ChatReq,
    Depends,
    ENRICH_COST,
    EnrichReq,
    HTTPException,
    LeadEnrichReq,
    OSINTEnrichReq,
    ObjectId,
    PersonReq,
    ProcessLeadsReq,
    PropertyReq,
    _active_ai_model,
    _charge_credits,
    _enrich_and_store,
    _enrich_one,
    _resolve_model,
    _save_enrichment,
    api,
    db,
    deepseek_chat,
    enrich_business,
    enrich_osint,
    enrich_person,
    enrich_property,
    get_current_user,
    os,
    require_admin,
    score_lead,
)


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
