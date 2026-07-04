"""NEXUS osint routes."""
from server import (
    Depends,
    DorkReq,
    MetaReq,
    PhoneReq,
    PortReq,
    ShodanReq,
    TargetReq,
    _save_report,
    api,
    asyncio,
    db,
    get_current_user,
    gov,
    httpx,
    re,
    socket,
)


@api.post("/osint/ip")
async def osint_ip(body: TargetReq, user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            geo = (await c.get(f"http://ip-api.com/json/{body.target}?fields=66846719")).json()
        except Exception:
            geo = {}
    res = {"tool": "ip_lookup", "target": body.target, "geo": geo}
    await _save_report(body.target, "ip_lookup", res, user)
    return res


@api.post("/osint/dns")
async def osint_dns(body: TargetReq, user: dict = Depends(get_current_user)):
    def run():
        import dns.resolver
        rec = {}
        for rt in ["A", "MX", "NS", "TXT"]:
            try:
                rec[rt] = [str(x) for x in dns.resolver.resolve(body.target, rt, lifetime=5)]
            except Exception:
                rec[rt] = []
        return rec
    records = await asyncio.to_thread(run)
    res = {"tool": "dns", "target": body.target, "records": records}
    await _save_report(body.target, "dns", res, user)
    return res


@api.post("/osint/whois")
async def osint_whois(body: TargetReq, user: dict = Depends(get_current_user)):
    def run():
        import whois as w
        try:
            return {k: str(v) for k, v in w.whois(body.target).items() if v}
        except Exception as e:
            return {"error": str(e)}
    data = await asyncio.to_thread(run)
    res = {"tool": "whois", "target": body.target, "data": data}
    await _save_report(body.target, "whois", res)
    return res


@api.post("/osint/phone")
async def osint_phone(body: PhoneReq, user: dict = Depends(get_current_user)):
    def run():
        import phonenumbers as pn
        from phonenumbers import geocoder, carrier
        try:
            p = pn.parse(body.target, body.region)
            return {"valid": pn.is_valid_number(p),
                    "international": pn.format_number(p, pn.PhoneNumberFormat.INTERNATIONAL),
                    "country": geocoder.description_for_number(p, "en"),
                    "carrier": carrier.name_for_number(p, "en")}
        except Exception as e:
            return {"error": str(e)}
    res = {"tool": "phone", "target": body.target, **(await asyncio.to_thread(run))}
    await _save_report(body.target, "phone", res, user)
    return res


@api.post("/osint/social")
async def osint_social(body: TargetReq, user: dict = Depends(get_current_user)):
    plats = {"instagram": f"https://www.instagram.com/{body.target}/",
             "twitter": f"https://twitter.com/{body.target}",
             "github": f"https://github.com/{body.target}",
             "reddit": f"https://www.reddit.com/user/{body.target}",
             "tiktok": f"https://www.tiktok.com/@{body.target}"}
    found = {}
    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
        for pl, url in plats.items():
            try:
                resp = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                found[pl] = {"exists": resp.status_code == 200, "url": url}
            except Exception:
                found[pl] = {"exists": False, "url": url}
    res = {"tool": "social", "target": body.target, "platforms": found}
    await _save_report(body.target, "social", res, user)
    return res


@api.post("/osint/geolocate")
async def osint_geo(body: TargetReq, user: dict = Depends(get_current_user)):
    def resolve():
        try:
            return socket.gethostbyname(body.target)
        except Exception:
            return body.target
    ip = await asyncio.to_thread(resolve)
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            geo = (await c.get(f"http://ip-api.com/json/{ip}?fields=66846719")).json()
        except Exception:
            geo = {}
    res = {"tool": "geolocate", "target": body.target, "ip": ip, "geo": geo}
    await _save_report(body.target, "geolocate", res, user)
    return res


@api.post("/osint/breach")
async def osint_breach(body: TargetReq, user: dict = Depends(get_current_user)):
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            resp = await c.get(f"https://haveibeenpwned.com/unifiedsearch/{body.target}",
                               headers={"User-Agent": "NEXUS-OSINT"})
            res = {"tool": "breach", "target": body.target,
                   "breached": resp.status_code == 200, "status": resp.status_code}
        except Exception as e:
            res = {"tool": "breach", "target": body.target, "error": str(e)}
    await _save_report(body.target, "breach", res, user)
    return res


@api.post("/osint/subdomains")
async def osint_subdomains(body: TargetReq, user: dict = Depends(get_current_user)):
    def run():
        subs = ["www", "mail", "api", "admin", "dev", "staging", "blog", "shop", "portal", "vpn", "remote"]
        found = []
        for s in subs:
            try:
                h = f"{s}.{body.target}"
                found.append({"subdomain": h, "ip": socket.gethostbyname(h)})
            except Exception:
                pass
        return found
    res = {"tool": "subdomains", "target": body.target, "found": await asyncio.to_thread(run)}
    await _save_report(body.target, "subdomains", res, user)
    return res


@api.post("/osint/portscan")
async def osint_portscan(body: PortReq, user: dict = Depends(get_current_user)):
    ports = body.ports or [21, 22, 25, 80, 443, 3306, 3389, 5432, 6379, 8080, 27017]
    def run():
        open_p = []
        for p in ports:
            try:
                s = socket.socket(); s.settimeout(1)
                if s.connect_ex((body.target, p)) == 0:
                    open_p.append(p)
                s.close()
            except Exception:
                pass
        return open_p
    res = {"tool": "portscan", "target": body.target, "open_ports": await asyncio.to_thread(run)}
    await _save_report(body.target, "portscan", res, user)
    return res


@api.post("/osint/metadata")
async def osint_metadata(body: MetaReq, user: dict = Depends(get_current_user)):
    ER = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    PHR = re.compile(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
    async with httpx.AsyncClient(timeout=12, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"}) as c:
        try:
            resp = await c.get(body.url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            txt = soup.get_text()
            res = {"tool": "metadata", "url": body.url,
                   "title": soup.title.string if soup.title else "",
                   "emails": list(set(ER.findall(txt)))[:20],
                   "phones": list(set(PHR.findall(txt)))[:20]}
        except Exception as e:
            res = {"tool": "metadata", "url": body.url, "error": str(e)}
    await _save_report(body.url, "metadata", res, user)
    return res


@api.post("/osint/shodan")
async def osint_shodan(body: ShodanReq, user: dict = Depends(get_current_user)):
    if not body.api_key:
        return {"tool": "shodan", "error": "No API key provided"}
    def run():
        try:
            import shodan
            r = shodan.Shodan(body.api_key).search(body.query, limit=10)
            return {"total": r["total"], "results": r["matches"][:5]}
        except Exception as e:
            return {"error": str(e)}
    return {"tool": "shodan", "query": body.query, **(await asyncio.to_thread(run))}


@api.post("/osint/dork")
async def osint_dork(body: DorkReq, user: dict = Depends(get_current_user)):
    def run():
        try:
            from googlesearch import search
            return list(search(body.dork, num_results=body.num))
        except Exception as e:
            return {"error": str(e)}
    out = await asyncio.to_thread(run)
    res = {"tool": "dork", "query": body.dork, "results": out}
    await _save_report(body.dork, "dork", res, user)
    return res


@api.get("/osint/reports")
async def osint_reports(limit: int = 50, user: dict = Depends(get_current_user)):
    cur = db.osint_reports.find(gov.tenant_scope(user), {"target": 1, "tool_used": 1, "created_at": 1}).sort("created_at", -1).limit(limit)
    return [{"id": str(r["_id"]), "target": r.get("target"), "tool": r.get("tool_used"),
             "created_at": r.get("created_at")} async for r in cur]
