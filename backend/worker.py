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
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import server  # noqa: E402  (reuse db + scrape logic)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - nexus-worker - %(levelname)s - %(message)s")
log = logging.getLogger("nexus-worker")


async def main():
    cfg = await server.get_scraper_config()
    interval = max(5, int(cfg.get("interval_min", 30)))
    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(server.run_scrape_cycle, "interval", minutes=interval,
                  id="scrape", replace_existing=True, max_instances=1,
                  next_run_time=datetime.datetime.now())
    sched.start()
    log.info("NEXUS worker online — scraping Tampa Bay services every %s min", interval)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
