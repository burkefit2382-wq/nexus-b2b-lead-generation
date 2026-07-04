"""NEXUS public routes."""
from server import (
    ChatDemoReq,
    Depends,
    EMAIL_RX,
    HTTPException,
    LeadDemoReq,
    Request,
    WaitlistReq,
    _lgvh_enrich,
    _lgvh_safe_answer,
    api,
    datetime,
    db,
    deepseek_chat,
    gov,
    logger,
    os,
    require_admin,
    timezone,
)


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
