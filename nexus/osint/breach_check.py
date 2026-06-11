"""Breach check and compromised credentials"""
import asyncio
import aiohttp
from typing import Dict, List
from nexus.utils.logger import logger


class BreachCheck:
    """Check for data breaches and compromised credentials"""

    def __init__(self, hibp_api_key: Optional[str] = None):
        self.hibp_api_key = hibp_api_key

    async def check_email_breaches(self, email: str) -> Dict:
        """Check if email was in data breaches via HaveIBeenPwned"""
        result = {
            'email': email,
            'breached': False,
            'breaches': [],
            'source': 'haveibeenpwned'
        }

        if not self.hibp_api_key:
            logger.warning("No HIBP API key provided")
            return result

        try:
            async with aiohttp.ClientSession() as session:
                headers = {'hibp-api-key': self.hibp_api_key, 'User-Agent': 'NEXUS-Intelligence-Suite'}
                async with session.get(
                    f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=true',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        breaches = await response.json()
                        result['breached'] = True
                        result['breaches'] = [
                            {
                                'name': b['Name'],
                                'title': b['Title'],
                                'breach_date': b['BreachDate'],
                                'added_date': b['AddedDate'],
                                'data_classes': b['DataClasses'],
                                'pwn_count': b['PwnCount']
                            }
                            for b in breaches
                        ]
                        logger.info(f"Found {len(breaches)} breaches for {email}")
                    elif response.status == 404:
                        result['breached'] = False
                    elif response.status == 401:
                        logger.error("Invalid HIBP API key")
                    elif response.status == 429:
                        logger.warning("HIBP rate limit exceeded")

        except Exception as e:
            logger.error(f"Breach check failed: {e}")

        return result

    async def check_password_breach(self, password_hash: str) -> Dict:
        """Check if password was breached via k-Anonymity"""
        result = {
            'found': False,
            'count': 0,
            'source': 'haveibeenpwned'
        }

        if not self.hibp_api_key:
            return result

        try:
            # Get first 5 characters of SHA-1 hash
            prefix = password_hash[:5]
            suffix = password_hash[5:].upper()

            async with aiohttp.ClientSession() as session:
                headers = {'hibp-api-key': self.hibp_api_key}
                async with session.get(
                    f'https://api.pwnedpasswords.com/range/{prefix}',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.text()

                        # Check if our suffix is in the response
                        for line in data.split('\r\n'):
                            if line.startswith(suffix):
                                count = int(line.split(':')[1])
                                result['found'] = True
                                result['count'] = count
                                logger.warning(f"Password found in {count} breaches")
                                break

        except Exception as e:
            logger.error(f"Password breach check failed: {e}")

        return result