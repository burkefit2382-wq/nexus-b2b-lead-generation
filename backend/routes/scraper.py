"""NEXUS scraper routes."""
from server import (
    APIFY_DAILY_BUDGET_USD,
    Depends,
    REDDIT_INTERVAL_MIN,
    RUN_SCHEDULER,
    SCRAPER_COUNTIES,
    SCRAPER_SECTORS,
    SCRAPER_STATE,
    ScraperConfig,
    _lead_pub,
    api,
    asyncio,
    datetime,
    db,
    get_current_user,
    get_scraper_config,
    os,
    require_admin,
    reschedule,
    run_reddit_cycle,
    run_scrape_cycle,
    scheduler,
    timezone,
)


@api.get("/scraper/status")
async def scraper_status(user: dict = Depends(get_current_user)):
    cfg = await get_scraper_config()
    job = scheduler.get_job("scrape")
    nxt = job.next_run_time.isoformat() if job and job.next_run_time else None
    rjob = scheduler.get_job("reddit")
    rnxt = rjob.next_run_time.isoformat() if rjob and rjob.next_run_time else None
    scraped = await db.leads.count_documents({"scraped": True})
    usage = await db.apify_usage.find_one({"_id": "usage"}) or {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reddit_spend = usage.get("spend", 0.0) if usage.get("date") == today else 0.0
    return {**SCRAPER_STATE, "next_run": nxt, "scheduler_running": scheduler.running,
            "enabled": cfg.get("enabled"), "interval_min": cfg.get("interval_min"),
            "min_score": cfg.get("min_score"), "total_scraped_leads": scraped,
            "reddit_next_run": rnxt, "reddit_enabled": bool(os.environ.get("APIFY_TOKEN")),
            "reddit_interval_min": REDDIT_INTERVAL_MIN,
            "reddit_spend_today_usd": round(reddit_spend, 2), "reddit_daily_budget_usd": APIFY_DAILY_BUDGET_USD}


@api.get("/intel/sources")
async def intel_sources(user: dict = Depends(get_current_user)):
    usage = await db.apify_usage.find_one({"_id": "usage"}) or {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spend = usage.get("spend", 0.0) if usage.get("date") == today else 0.0
    has = lambda k: bool(os.environ.get(k))
    return {"apify_spend_today_usd": round(spend, 2), "apify_budget_usd": APIFY_DAILY_BUDGET_USD,
            "sources": [
                {"key": "osm", "name": "OpenStreetMap / Overpass — B2B firms", "status": "live",
                 "cost": "free", "detail": f"{len(SCRAPER_SECTORS)} HQ sectors × {len(SCRAPER_COUNTIES)} counties, OSINT-filtered, every 30 min"},
                {"key": "reddit", "name": "Reddit (via Apify)", "status": "live" if has("APIFY_TOKEN") else "inactive",
                 "cost": f"${spend:.2f} / ${APIFY_DAILY_BUDGET_USD:.0f} today", "detail": "hourly, $5/day budget guard"},
                {"key": "shodan", "name": "Shodan — host & CVE intel", "status": "live" if has("SHODAN_API_KEY") else "inactive",
                 "cost": "oss plan", "detail": "enriches Threat Intel scans"},
                {"key": "dns", "name": "DNS · DNSSEC · SSL/TLS", "status": "live",
                 "cost": "free", "detail": "records, cert expiry, weak protocols"},
                {"key": "email", "name": "Resend — pitch sending", "status": "live" if has("RESEND_API_KEY") else "inactive",
                 "cost": "free tier", "detail": os.environ.get("SENDER_EMAIL", "")},
            ]}


@api.post("/scraper/trigger")
async def scraper_trigger(source: str = "all", user: dict = Depends(get_current_user)):
    if source == "reddit":
        asyncio.create_task(run_reddit_cycle("manual"))
        return {"triggered": True, "status": "reddit cycle started"}
    asyncio.create_task(run_scrape_cycle("manual"))
    if source == "all":
        asyncio.create_task(run_reddit_cycle("manual"))
    return {"triggered": True, "status": "cycle started"}


@api.get("/scraper/config")
async def scraper_get_config(user: dict = Depends(get_current_user)):
    cfg = await get_scraper_config()
    cfg.pop("_id", None)
    return cfg


@api.put("/scraper/config")
async def scraper_set_config(body: ScraperConfig, user: dict = Depends(require_admin)):
    data = body.model_dump()
    await db.scraper_config.update_one({"_id": "config"}, {"$set": data}, upsert=True)
    if data["enabled"] and RUN_SCHEDULER:
        reschedule(data["interval_min"])
        if not scheduler.running:
            scheduler.start()
    else:
        try: scheduler.remove_job("scrape")
        except Exception: pass
    return {"updated": True, **data}


@api.get("/scraper/feed")
async def scraper_feed(limit: int = 30, user: dict = Depends(get_current_user)):
    cur = db.leads.find({"scraped": True}).sort("created_at", -1).limit(limit)
    return [_lead_pub(l) async for l in cur]
