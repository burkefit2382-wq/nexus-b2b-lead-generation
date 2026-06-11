"""LinkedIn company intelligence scraper"""
import asyncio
from typing import Dict, Optional
from playwright.async_api import async_playwright
from nexus.utils.logger import logger


class LinkedInScraper:
    """LinkedIn company intelligence scraper"""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.authenticated = False

    async def login(self):
        """Login to LinkedIn"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto('https://www.linkedin.com/login')
                await page.fill('#username', self.email)
                await page.fill('#password', self.password)
                await page.click('button[type="submit"]')
                await page.wait_for_timeout(3000)

                # Check if login successful
                if 'checkpoint' not in page.url:
                    self.authenticated = True
                    logger.info("LinkedIn login successful")
                else:
                    logger.error("LinkedIn login required manual verification")

            except Exception as e:
                logger.error(f"LinkedIn login failed: {e}")

            await browser.close()

    async def get_company_info(self, company_url: str) -> Optional[Dict]:
        """Get company information from LinkedIn"""
        if not self.authenticated:
            await self.login()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(company_url)
                await page.wait_for_timeout(2000)

                # Extract company data
                name_elem = await page.query_selector('h1')
                name = await name_elem.inner_text() if name_elem else None

                followers_elem = await page.query_selector('span.t-black--light')
                followers = await followers_elem.inner_text() if followers_elem else None

                info = {
                    'name': name,
                    'followers': followers,
                    'url': company_url,
                    'source': 'linkedin'
                }

                logger.info(f"Extracted LinkedIn info for {name}")
                return info

            except Exception as e:
                logger.error(f"LinkedIn scrape failed: {e}")
                return None
            finally:
                await browser.close()