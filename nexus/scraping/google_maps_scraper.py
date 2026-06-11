"""Google Maps business scraper"""
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
from nexus.utils.logger import logger


class GoogleMapsScraper:
    """Google Maps business scraper"""

    async def search_businesses(
        self,
        query: str,
        location: str,
        limit: int = 20
    ) -> List[Dict]:
        """Search for businesses on Google Maps"""
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                search_url = f"https://www.google.com/maps/search/{query}+{location}"
                await page.goto(search_url)
                await page.wait_for_timeout(3000)

                # Wait for results
                await page.wait_for_selector('div[role="article"]', timeout=10000)

                # Extract business listings
                businesses = await page.query_selector_all('div[role="article"]')

                for business in businesses[:limit]:
                    try:
                        name_elem = await business.query_selector('h3')
                        name = await name_elem.inner_text() if name_elem else "N/A"

                        rating_elem = await business.query_selector('span[aria-label*="stars"]')
                        rating = await rating_elem.get_attribute('aria-label') if rating_elem else None

                        results.append({
                            'name': name,
                            'rating': rating,
                            'source': 'google_maps',
                            'search_query': query
                        })
                    except Exception as e:
                        logger.warning(f"Error extracting business: {e}")
                        continue

            except Exception as e:
                logger.error(f"Google Maps scrape failed: {e}")

            await browser.close()

        logger.info(f"Found {len(results)} businesses")
        return results