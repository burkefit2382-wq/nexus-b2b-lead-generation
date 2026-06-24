from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import LeadSearchRequest, LeadSearchResponse
from .osint import generate_leads

app = FastAPI(
    title="NEXUS Intelligence API",
    description="Autonomous OSINT & AI-Driven B2B Lead Generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/leads/search", response_model=LeadSearchResponse)
def search_leads(request: LeadSearchRequest) -> LeadSearchResponse:
    leads = generate_leads(
        company_name=request.company_name,
        industry=request.industry,
        location=request.location,
        limit=request.limit,
    )
    return LeadSearchResponse(
        leads=leads,
        total=len(leads),
        query=request.company_name,
    )


@app.get("/api/leads/search", response_model=LeadSearchResponse)
def search_leads_get(
    company_name: str = Query(..., description="Target company name"),
    industry: str | None = Query(None),
    location: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> LeadSearchResponse:
    leads = generate_leads(
        company_name=company_name,
        industry=industry,
        location=location,
        limit=limit,
    )
    return LeadSearchResponse(
        leads=leads,
        total=len(leads),
        query=company_name,
    )
