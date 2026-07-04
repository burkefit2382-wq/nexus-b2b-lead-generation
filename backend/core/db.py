"""Shared MongoDB runtime state.

The Motor client MUST be created inside the running event loop (in the FastAPI
startup handler / worker main), not at import time — creating it at import binds
to a loop that doesn't exist yet and silently breaks connections under MongoDB
Atlas (mongodb+srv) in production.

`db` is a lazy proxy that forwards attribute/item access to the live database at
call time, so modules can `from core.db import db` at import without capturing a
None before startup runs.
"""
import os

from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

_state = {"client": None, "db": None}


class _DBProxy:
    def __getattr__(self, name):
        real = _state["db"]
        if real is None:
            raise RuntimeError("Database not initialized — call core.db.init_db() first.")
        return getattr(real, name)

    def __getitem__(self, name):
        real = _state["db"]
        if real is None:
            raise RuntimeError("Database not initialized — call core.db.init_db() first.")
        return real[name]


db = _DBProxy()


def init_db():
    """Create the Motor client inside the running event loop and bind the db."""
    _state["client"] = AsyncIOMotorClient(mongo_url)
    _state["db"] = _state["client"][db_name]
    return db


def get_client():
    return _state["client"]


def close():
    if _state["client"] is not None:
        _state["client"].close()
