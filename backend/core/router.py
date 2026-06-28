"""The single shared /api router. All route modules attach their handlers to this
instance; server.py mounts it once via app.include_router(api)."""
from fastapi import APIRouter

api = APIRouter(prefix="/api")
