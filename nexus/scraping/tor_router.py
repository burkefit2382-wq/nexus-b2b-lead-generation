"""Tor routing for anonymous scraping"""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser
from nexus.config import settings
from nexus.utils.logger import logger


class TorRouter:
    """Tor routing for anonymous scraping"""

    def __init__(self):
        self.proxy = f"socks5://localhost:{settings.TOR_PORT}" if settings.TOR_ENABLED else None

    async def is_tor_running(self) -> bool:
        """Check if Tor is running"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', settings.TOR_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def get_browser(self) -> Optional[Browser]:
        """Get browser with Tor proxy"""
        if not settings.TOR_ENABLED:
            return None

        if not await self.is_tor_running():
            logger.error("Tor is not running")
            return None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": self.proxy}
            )
            return browser

    async def check_ip(self) -> Optional[str]:
        """Check current IP address"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto('https://check.torproject.org/')
                ip_elem = await page.query_selector('strong')
                ip = await ip.inner_text() if ip_elem else None
                logger.info(f"Current IP: {ip}")
                return ip
            except Exception as e:
                logger.error(f"IP check failed: {e}")
                return None
            finally:
                await browser.close()