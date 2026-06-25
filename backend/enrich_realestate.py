"""Deep Llama 3 + OSINT re-enrichment of existing Pinellas real-estate leads (quality pass).
Updates each lead in place by _id (no duplicates)."""
import asyncio
from datetime import datetime, timezone
import server
from server import (_llama_assess, _osint_verify_sync, _data_confidence, _operational_tier,
                    TIER_CREDITS, STOREFRONT_MIN_CONFIDENCE, AsyncIOMotorClient, mongo_url, db_name)

CONCURRENCY = 5


async def main():
    server.client = AsyncIOMotorClient(mongo_url)
    server.db = server.client[db_name]
    db = server.db
    leads = [l async for l in db.leads.find({"category": "real_estate"})]
    print(f"enriching {len(leads)} real_estate leads with Llama 3 + OSINT")
    sem = asyncio.Semaphore(CONCURRENCY)
    now = datetime.now(timezone.utc).isoformat()
    stats = {"done": 0, "ready": 0, "errors": 0}

    async def process(l):
        company = (l.get("company") or "").strip()
        city = (l.get("city") or "").strip()
        try:
            async with sem:
                ai = await _llama_assess(l.get("category", "real_estate"),
                                         l.get("raw_text", ""), company, "llama")
            v = await asyncio.to_thread(_osint_verify_sync, l.get("email", ""), l.get("phone", ""),
                                        l.get("website", ""), company, city, l.get("state", "FL"))
            intent = int(ai.get("intent_score") or 0)
            conf = _data_confidence(v, intent)
            risk = list(v["risk"])
            for f in (ai.get("anomaly_flags") or []):
                if isinstance(f, str) and f.strip():
                    risk.append({"flag": f.strip()[:80], "severity": "medium", "source": "ai_analyst"})
            if ai.get("entity_consistency") == "low":
                risk.append({"flag": "Unverified_Entity_Structure", "severity": "high"})
            tier = _operational_tier(conf, intent)
            nodes = v["nodes"]
            ready = conf >= STOREFRONT_MIN_CONFIDENCE and len(nodes) >= 2
            tags = ai.get("category_tags")
            tags = ",".join([str(t) for t in tags]) if isinstance(tags, list) and tags else "real_estate,pinellas,florida"
            upd = {
                "ai_summary": ai.get("summary") or l.get("ai_summary", ""),
                "ai_budget_est": ai.get("budget_estimate") or "", "ai_intent_score": intent,
                "entity_consistency": ai.get("entity_consistency", "low"), "tags": tags,
                "score": conf, "quality_score": conf, "data_confidence_score": conf,
                "cross_verification": nodes, "risk_matrix": risk,
                "operational_value_tier": tier, "price_per_lead": TIER_CREDITS[tier],
                "status": "ready_to_sell" if ready else "enriched",
                "enriched_at": now, "enrichment_model": server._active_ai_model("llama"),
            }
            if l.get("purchase_status") != "sold":
                upd["ready_to_sell"] = ready
            await db.leads.update_one({"_id": l["_id"]}, {"$set": upd})
            if ready:
                stats["ready"] += 1
        except Exception as e:
            stats["errors"] += 1
            print("err", company, str(e)[:80])
        finally:
            stats["done"] += 1

    await asyncio.gather(*(process(l) for l in leads))
    avail = await db.leads.count_documents(
        {"category": "real_estate", "ready_to_sell": True, "purchase_status": "available"})
    total = await db.leads.count_documents({"category": "real_estate"})
    print(f"DONE done={stats['done']} ready={stats['ready']} errors={stats['errors']} "
          f"| real_estate total={total} available_in_storefront={avail}")

if __name__ == "__main__":
    asyncio.run(main())
