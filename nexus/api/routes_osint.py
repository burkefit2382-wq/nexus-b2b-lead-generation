"""OSINT API routes"""
from fastapi import APIRouter, HTTPException
from typing import Dict
from nexus.osint.email_lookup import EmailLookup
from nexus.osint.phone_lookup import PhoneLookup
from nexus.osint.domain_intel import DomainIntel
from nexus.osint.breach_check import BreachCheck
from nexus.utils.logger import logger

router = APIRouter()

# Initialize OSINT modules
email_lookup = EmailLookup()
phone_lookup = PhoneLookup()
domain_intel = DomainIntel()
breach_check = BreachCheck()


@router.post("/email/verify")
async def verify_email(email: str):
    """Verify email address"""
    try:
        result = await email_lookup.verify_email(email)
        return result
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email/breaches")
async def check_email_breaches(email: str):
    """Check email for data breaches"""
    try:
        result = await breach_check.check_email_breaches(email)
        return result
    except Exception as e:
        logger.error(f"Breach check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phone/parse")
async def parse_phone(phone: str):
    """Parse and validate phone number"""
    try:
        result = phone_lookup.parse_phone(phone)
        return result
    except Exception as e:
        logger.error(f"Phone parsing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain/whois")
async def get_domain_whois(domain: str):
    """Get WHOIS information for domain"""
    try:
        result = await domain_intel.get_whois(domain)
        return result
    except Exception as e:
        logger.error(f"WHOIS lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain/dns")
async def get_domain_dns(domain: str):
    """Get DNS records for domain"""
    try:
        result = await domain_intel.get_dns_records(domain)
        return result
    except Exception as e:
        logger.error(f"DNS lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain/reputation")
async def get_domain_reputation(domain: str):
    """Get domain reputation"""
    try:
        result = await domain_intel.check_reputation(domain)
        return result
    except Exception as e:
        logger.error(f"Reputation check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))