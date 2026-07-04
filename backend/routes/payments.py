"""NEXUS payments routes."""
from server import (
    CREDIT_PACKAGES,
    CheckoutReq,
    Depends,
    HTTPException,
    ObjectId,
    Request,
    _settle_payment,
    api,
    datetime,
    db,
    get_current_user,
    os,
    timezone,
)


@api.get("/payments/packages")
async def payment_packages(user: dict = Depends(get_current_user)):
    return [{"id": k, **v} for k, v in CREDIT_PACKAGES.items()]


@api.post("/payments/checkout")
async def payment_checkout(body: CheckoutReq, request: Request, user: dict = Depends(get_current_user)):
    pkg = CREDIT_PACKAGES.get(body.package_id)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")
    # open-redirect guard: only allow same-host or trusted origins
    from urllib.parse import urlparse
    o = urlparse(body.origin_url)
    host = (o.hostname or "")
    req_host = (request.base_url.hostname or "")
    if o.scheme not in ("http", "https") or not (
        host == req_host or host.endswith("emergentagent.com") or host in ("localhost", "127.0.0.1")):
        raise HTTPException(status_code=400, detail="Invalid origin")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"], webhook_url=webhook_url)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/"
    meta = {"user_id": user["id"], "package_id": body.package_id, "credits": str(pkg["credits"])}
    req = CheckoutSessionRequest(amount=float(pkg["amount"]), currency="usd",
                                 success_url=success_url, cancel_url=cancel_url, metadata=meta)
    session = await sc.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": user["id"], "package_id": body.package_id,
        "amount": float(pkg["amount"]), "currency": "usd", "credits": pkg["credits"],
        "payment_status": "pending", "status": "initiated", "metadata": meta,
        "created_at": datetime.now(timezone.utc).isoformat()})
    return {"url": session.url, "session_id": session.session_id}


@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id})
    if not txn or (txn["user_id"] != user["id"] and user.get("role") != "admin"):
        raise HTTPException(status_code=404, detail="Transaction not found")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    sc = StripeCheckout(api_key=os.environ["STRIPE_API_KEY"],
                        webhook_url=f"{str(request.base_url)}api/webhook/stripe")
    cs = await sc.get_checkout_status(session_id)
    await _settle_payment(session_id, cs.payment_status)
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    return {"status": cs.status, "payment_status": cs.payment_status,
            "amount_total": cs.amount_total, "currency": cs.currency,
            "kind": txn.get("kind", "credits"), "lead_id": txn.get("lead_id"),
            "credits": (u or {}).get("credits", 0)}
