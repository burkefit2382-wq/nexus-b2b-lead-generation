"""Email lookup and verification"""
import asyncio
import aiohttp
from typing import Dict, Optional
from nexus.utils.logger import logger


class EmailLookup:
    """Email lookup and verification"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def verify_email(self, email: str) -> Dict:
        """Verify email address"""
        result = {
            'email': email,
            'valid': False,
            'disposable': False,
            'deliverable': False,
            'source': 'email_lookup'
        }

        try:
            # Basic format validation
            if '@' not in email:
                return result

            domain = email.split('@')[1]

            # Check MX records
            import dns.resolver
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                result['valid'] = True
                result['deliverable'] = len(mx_records) > 0
            except:
                result['deliverable'] = False

            # Check disposable domains
            disposable_domains = ['tempmail.com', 'guerrillamail.com', 'mailinator.com']
            result['disposable'] = domain in disposable_domains

        except Exception as e:
            logger.error(f"Email verification failed: {e}")

        return result

    async def check_breaches(self, email: str) -> Dict:
        """Check if email was in data breaches"""
        result = {
            'email': email,
            'breached': False,
            'breaches_count': 0,
            'breaches': [],
            'source': 'breach_check'
        }

        try:
            # Call HaveIBeenPwned API (requires API key)
            if self.api_key:
                async with aiohttp.ClientSession() as session:
                    headers = {'hibp-api-key': self.api_key}
                    async with session.get(
                        f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            breaches = await response.json()
                            result['breached'] = True
                            result['breaches_count'] = len(breaches)
                            result['breaches'] = [
                                {
                                    'name': b['Name'],
                                    'date': b['BreachDate'],
                                    'data_classes': b['DataClasses']
                                }
                                for b in breaches
                            ]
        except Exception as e:
            logger.warning(f"Breach check failed: {e}")

        return result