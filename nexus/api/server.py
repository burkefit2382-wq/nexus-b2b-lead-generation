"""FastAPI server"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from nexus.config import settings
from nexus.utils.logger import logger

# Import routes
from nexus.api import routes_leads, routes_osint, routes_ai

app = FastAPI(
    title="NEXUS B2B Lead Generation API",
    description="Advanced OSINT and lead generation platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(routes_osint.router, prefix="/api/osint", tags=["OSINT"])
app.include_router(routes_ai.router, prefix="/api/ai", tags=["AI"])

# Serve static files
app.mount("/static", StaticFiles(directory="nexus/dashboard"), name="static")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NEXUS B2B Lead Generation API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "dashboard": "/static/index.html"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info("NEXUS API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("NEXUS API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)