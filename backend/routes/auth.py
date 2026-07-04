"""NEXUS auth routes."""
from server import (
    Depends,
    HTTPException,
    JWT_ALGORITHM,
    LoginReq,
    ObjectId,
    RegisterReq,
    Request,
    Response,
    _pub,
    api,
    create_access_token,
    create_refresh_token,
    datetime,
    db,
    get_current_user,
    get_jwt_secret,
    gov,
    hash_password,
    jwt,
    secrets,
    set_auth_cookies,
    timezone,
    verify_password,
)


@api.post("/auth/register")
async def register(body: RegisterReq, request: Request, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    # Provision an isolated tenant (org) for this operator — they administer their own workspace.
    tenant_id = secrets.token_hex(8)
    domain_part = email.split("@")[-1].split(".")[0] if "@" in email else "operator"
    org_name = (body.org_name or "").strip() or f"{domain_part.title()} Org"
    await db.tenants.insert_one({
        "tenant_id": tenant_id, "name": org_name, "owner_email": email, "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()})
    doc = {"email": email, "password_hash": hash_password(body.password),
           "name": body.name, "role": "tenant_admin", "credits": 0,
           "tenant_id": tenant_id, "tenant_name": org_name,
           "created_at": datetime.now(timezone.utc).isoformat()}
    res = await db.users.insert_one(doc)
    uid = str(res.inserted_id)
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    await gov.audit_log("user.register", user={"id": uid, **doc}, request=request,
                        target=tenant_id, meta={"org": org_name})
    return _pub({"id": uid, **doc})


@api.post("/auth/login")
async def login(body: LoginReq, request: Request, response: Response):
    email = body.email.lower()
    await gov.check_lockout(request, email)
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await gov.record_failed_login(request, email)
        await gov.audit_log("user.login", user={"email": email}, request=request,
                            status="failure", meta={"reason": "bad_credentials"})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await gov.clear_login_attempts(request, email)
    uid = str(user["_id"])
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    await gov.audit_log("user.login", user={"id": uid, **user}, request=request)
    return _pub({"id": uid, **user})


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(rt, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        uid = str(user["_id"])
        access = create_access_token(uid, user["email"])
        response.set_cookie("access_token", access, httponly=True, secure=False,
                            samesite="lax", max_age=43200, path="/")
        return {"refreshed": True}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return _pub(user)
