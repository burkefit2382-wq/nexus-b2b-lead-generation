"""NEXUS standalone scraper worker.

Runs the 24/7 lead-scraping scheduler OUTSIDE the FastAPI process so the API can
scale to multiple workers without duplicating scrape cycles. In production the API
container runs with RUN_SCHEDULER=false and a single instance of this worker owns
the schedule.

Reuses the scrape logic from server.py (db, run_scrape_cycle, get_scraper_config).
"""
import asyncio
import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import server  # noqa: E402  (reuse db + scrape logic)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - nexus-worker - %(levelname)s - %(message)s")
log = logging.getLogger("nexus-worker")


async def main():
    # Motor client must be created inside the running event loop (mirrors server startup).
    server.init_db()
    log.info("Worker: MongoDB client initialized inside event loop")
    cfg = await server.get_scraper_config()
    interval = max(5, int(cfg.get("interval_min", 30)))
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(server.run_scrape_cycle, "interval", minutes=interval,
                  id="scrape", replace_existing=True, max_instances=1,
                  next_run_time=datetime.datetime.now())
    sched.add_job(server.run_reddit_cycle, "interval", minutes=max(15, server.REDDIT_INTERVAL_MIN),
                  id="reddit", replace_existing=True, max_instances=1)
    sched.start()
    log.info("NEXUS worker online — OSM every %s min, Reddit every %s min", interval, server.REDDIT_INTERVAL_MIN)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
