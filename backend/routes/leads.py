"""NEXUS leads routes."""
from server import (
    Depends,
    HTTPException,
    LeadBuyReq,
    LeadCreate,
    ObjectId,
    Optional,
    Request,
    StreamingResponse,
    _lead_pub,
    api,
    datetime,
    db,
    get_current_user,
    lead_price,
    os,
    re,
    timezone,
)


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
