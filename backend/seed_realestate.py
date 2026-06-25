"""One-off: generate REAL Pinellas County real-estate leads from OpenStreetMap,
verify via OSINT, and store as ready_to_sell intel packages."""
import asyncio
from datetime import datetime, timezone
from urllib.parse import quote
import httpx
import server
from server import (_osint_verify_sync, _data_confidence, _operational_tier, TIER_CREDITS,
                    AsyncIOMotorClient, mongo_url, db_name)

UA = {"User-Agent": "NEXUS-LeadBot/1.0 (contact: nexus@local)"}
OVERPASS = "https://overpass-api.de/api/interpreter"
OVERPASS_Q = """
[out:json][timeout:90];
area["name"="Pinellas County"]["admin_level"="6"]->.a;
(
  node["office"="estate_agent"](area.a);
  way["office"="estate_agent"](area.a);
  node["shop"="estate_agent"](area.a);
  way["shop"="estate_agent"](area.a);
  node["office"="property_management"](area.a);
  way["office"="property_management"](area.a);
);
out center tags;
"""
PINELLAS_CITIES = [
    "Clearwater FL", "St Petersburg FL", "Largo FL", "Pinellas Park FL", "Palm Harbor FL",
    "Tarpon Springs FL", "Dunedin FL", "Seminole FL", "Safety Harbor FL", "Oldsmar FL",
    "Gulfport FL", "Belleair FL", "St Pete Beach FL", "Tampa FL",
]
RE_QUERIES = ["real estate agency", "realtor", "real estate broker", "property management"]
TARGET = 200


def _norm(raw):
    name = raw.get("company", "").strip()
    city = raw.get("city", "").strip()
    return (name.lower(), city.lower())


async def fetch_overpass(client):
    out = []
    try:
        r = await client.post(OVERPASS, data={"data": OVERPASS_Q})
        els = r.json().get("elements", [])
    except Exception as e:
        print("overpass error:", e)
        els = []
    for e in els:
        t = e.get("tags", {})
        name = t.get("name") or t.get("operator") or ""
        if not name:
            continue
        out.append({
            "company": name,
            "website": t.get("website") or t.get("contact:website") or "",
            "phone": t.get("phone") or t.get("contact:phone") or "",
            "email": t.get("email") or t.get("contact:email") or "",
            "city": t.get("addr:city") or "", "state": t.get("addr:state") or "FL",
            "street": t.get("addr:street", ""),
        })
    print(f"overpass returned {len(out)} estate entities")
    return out


async def fetch_nominatim(client, need):
    out = []
    for q in RE_QUERIES:
        for loc in PINELLAS_CITIES:
            if len(out) >= need:
                return out
            url = (f"https://nominatim.openstreetmap.org/search?q={quote(q + ', ' + loc)}"
                   "&format=jsonv2&extratags=1&addressdetails=1&limit=40&countrycodes=us")
            try:
                data = (await client.get(url)).json()
            except Exception:
                data = []
            for r in (data or []):
                et = r.get("extratags") or {}
                ad = r.get("address") or {}
                name = r.get("name") or et.get("operator") or ""
                if not name:
                    continue
                city = ad.get("city") or ad.get("town") or ad.get("village") or ad.get("municipality") or ""
                out.append({
                    "company": name,
                    "website": et.get("website") or et.get("contact:website") or "",
                    "phone": et.get("phone") or et.get("contact:phone") or "",
                    "email": et.get("email") or et.get("contact:email") or "",
                    "city": city, "state": "FL", "street": ad.get("road", ""),
                })
            await asyncio.sleep(1.1)
    print(f"nominatim returned {len(out)} candidates")
    return out


async def main():
    server.client = AsyncIOMotorClient(mongo_url)
    server.db = server.client[db_name]
    db = server.db
    async with httpx.AsyncClient(timeout=120, headers=UA, follow_redirects=True) as c:
        raws = await fetch_overpass(c)
        seen = set(_norm(r) for r in raws)
        if len([r for r in raws]) < TARGET + 40:
            extra = await fetch_nominatim(c, TARGET + 80)
            for r in extra:
                k = _norm(r)
                if k[0] and k not in seen:
                    seen.add(k)
                    raws.append(r)
    print(f"total unique candidates: {len(raws)}")

    sem = asyncio.Semaphore(25)
    now = datetime.now(timezone.utc).isoformat()
    stats = {"inserted": 0, "updated": 0, "ready": 0}

    async def process(raw):
        company = raw["company"].strip()
        city = raw["city"].strip()
        async with sem:
            v = await asyncio.to_thread(_osint_verify_sync, raw["email"], raw["phone"],
                                        raw["website"], company, city, raw["state"])
        intent = 40 + (20 if raw["website"] else 0) + (15 if raw["phone"] else 0)
        conf = _data_confidence(v, intent)
        tier = _operational_tier(conf, intent)
        nodes = v["nodes"]
        ready = conf >= 50 and len(nodes) >= 2
        if ready:
            stats["ready"] += 1
        loc = ", ".join([x for x in [city, "FL"] if x])
        doc = {
            "category": "real_estate", "full_name": "", "company": company,
            "email": raw["email"], "phone": raw["phone"], "website": raw["website"],
            "city": city, "state": "FL",
            "source_site": "OpenStreetMap", "source": "osm_pinellas_realestate",
            "source_url": raw["website"] or "",
            "raw_text": f"{company} — real estate / property firm in {loc}. {raw['website']} {raw['phone']}".strip(),
            "ai_summary": f"Real estate firm operating in {loc} (Pinellas County).",
            "ai_budget_est": "", "ai_intent_score": intent,
            "tags": "real_estate,pinellas,florida", "score": conf, "quality_score": conf,
            "data_confidence_score": conf, "cross_verification": nodes, "risk_matrix": list(v["risk"]),
            "operational_value_tier": tier, "price_per_lead": TIER_CREDITS[tier],
            "ready_to_sell": ready, "status": "ready_to_sell" if ready else "enriched",
            "enriched_at": now, "enrichment_model": "osint_verify",
        }
        existing = await db.leads.find_one(
            {"company": company, "city": city, "source": "osm_pinellas_realestate"})
        if existing:
            if existing.get("purchase_status") == "sold":
                doc.pop("ready_to_sell", None)
            await db.leads.update_one({"_id": existing["_id"]}, {"$set": doc})
            stats["updated"] += 1
        else:
            doc.update({"is_sold": False, "sold_price": 0.0, "purchase_status": "available",
                        "buyer_user_id": None, "created_at": now})
            await db.leads.insert_one(doc)
            stats["inserted"] += 1

    await asyncio.gather(*(process(r) for r in raws))
    total = await db.leads.count_documents({"category": "real_estate"})
    avail = await db.leads.count_documents(
        {"category": "real_estate", "ready_to_sell": True, "purchase_status": "available"})
    print(f"DONE inserted={stats['inserted']} updated={stats['updated']} "
          f"ready={stats['ready']} | real_estate total={total} available_in_storefront={avail}")

if __name__ == "__main__":
    asyncio.run(main())
