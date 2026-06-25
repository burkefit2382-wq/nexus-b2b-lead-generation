import uuid
import hashlib
from typing import Optional
from .models import Lead


def _stable_id(seed: str) -> str:
    return hashlib.md5(seed.encode()).hexdigest()[:12]


def generate_leads(
    company_name: str,
    industry: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> list[Lead]:
    """
    Generate enriched B2B leads for a target company using OSINT signals.

    In production this would call external data sources (LinkedIn, Hunter.io,
    Clearbit, etc.). This implementation returns deterministic stub data so
    that the service can be deployed and tested without live API keys.
    """
    roles = [
        ("Alice Johnson", "VP of Sales"),
        ("Bob Martinez", "CTO"),
        ("Carol Williams", "Head of Marketing"),
        ("David Lee", "Director of Operations"),
        ("Eve Brown", "Chief Revenue Officer"),
        ("Frank Garcia", "Product Manager"),
        ("Grace Kim", "Business Development Manager"),
        ("Henry Chen", "CEO"),
        ("Iris Patel", "VP of Engineering"),
        ("James Wilson", "CFO"),
    ]

    leads: list[Lead] = []
    for i, (name, role) in enumerate(roles[:limit]):
        slug = f"{company_name}-{name}".lower().replace(" ", "-")
        domain = f"{company_name.lower().replace(' ', '')}.com"
        email_local = name.lower().replace(" ", ".")
        leads.append(
            Lead(
                id=_stable_id(slug),
                company=company_name,
                contact_name=f"{name} ({role})",
                email=f"{email_local}@{domain}",
                phone=f"+1-555-{100 + i:03d}-{200 + i:04d}",
                website=f"https://www.{domain}",
                industry=industry or "Technology",
                location=location or "United States",
                score=max(40, 95 - i * 5),
            )
        )
    return leads
