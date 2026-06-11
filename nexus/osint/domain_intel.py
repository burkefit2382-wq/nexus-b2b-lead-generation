"""Domain intelligence and reputation"""
import asyncio
import dns.resolver
import whois
from typing import Dict, Optional
from nexus.utils.logger import logger


class DomainIntel:
    """Domain intelligence and reputation"""

    async def get_whois(self, domain: str) -> Dict:
        """Get WHOIS information"""
        result = {
            'domain': domain,
            'registered': False,
            'registrar': None,
            'created_date': None,
            'expiration_date': None,
            'name_servers': [],
            'source': 'whois'
        }

        try:
            w = whois.whois(domain)

            result['registered'] = True
            result['registrar'] = w.registrar
            result['created_date'] = str(w.creation_date) if w.creation_date else None
            result['expiration_date'] = str(w.expiration_date) if w.expiration_date else None
            result['name_servers'] = w.name_servers or []

        except Exception as e:
            logger.warning(f"WHOIS lookup failed for {domain}: {e}")

        return result

    async def get_dns_records(self, domain: str) -> Dict:
        """Get DNS records"""
        result = {
            'domain': domain,
            'a_records': [],
            'mx_records': [],
            'txt_records': [],
            'ns_records': [],
            'source': 'dns'
        }

        try:
            # A records
            try:
                a_records = dns.resolver.resolve(domain, 'A')
                result['a_records'] = [str(r) for r in a_records]
            except:
                pass

            # MX records
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                result['mx_records'] = [str(r) for r in mx_records]
            except:
                pass

            # TXT records
            try:
                txt_records = dns.resolver.resolve(domain, 'TXT')
                result['txt_records'] = [str(r) for r in txt_records]
            except:
                pass

        except Exception as e:
            logger.error(f"DNS lookup failed: {e}")

        return result

    async def check_reputation(self, domain: str) -> Dict:
        """Check domain reputation"""
        result = {
            'domain': domain,
            'blacklisted': False,
            'risk_score': 0,
            'categories': [],
            'source': 'reputation'
        }

        # Would integrate with VirusTotal/URLVoid API here
        return result