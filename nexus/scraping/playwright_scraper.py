"""Playwright-based web scraper"""
import asyncio
from typing import Optional, List
from playwright.async_api import async_playwright, Page
from nexus.config import settings
from nexus.utils.logger import logger


class PlaywrightScraper:
    """Playwright-based scraper"""

    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        """Start browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS
        )
        logger.info("Playwright browser started")

    async def stop(self):
        """Stop browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright browser stopped")

    async def scrape_page(self, url: str, selector: Optional[str] = None) -> str:
        """Scrape single page"""
        if not self.browser:
            await self.start()

        page = await self.browser.new_page()
        try:
            await page.goto(url, timeout=settings.PLAYWRIGHT_TIMEOUT)

            if selector:
                element = await page.wait_for_selector(selector, timeout=10000)
                content = await element.inner_text()
            else:
                content = await page.inner_text("body")

            return content
        finally:
            await page.close()

    async def scrape_multiple(self, urls: List[str]) -> List[str]:
        """Scrape multiple pages concurrently"""
        tasks = [self.scrape_page(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)