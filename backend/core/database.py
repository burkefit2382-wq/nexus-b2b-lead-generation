"""Shared MongoDB accessor.

The Motor client must be created INSIDE the running event loop (in the FastAPI
startup event / worker main), not at import time — creating it at import binds to
a loop that doesn't exist yet and silently breaks connections under Atlas
(mongodb+srv). `db` is a lazy proxy so modules can `from core.database import db`
at import time and have it resolve to the real database once `init_db()` runs.
"""


class _DBProxy:
    _db = None
    _client = None

    def __getattr__(self, name):
        if _DBProxy._db is None:
            raise RuntimeError("Database not initialized — call init_db() first")
        return getattr(_DBProxy._db, name)

    def __getitem__(self, name):
        if _DBProxy._db is None:
            raise RuntimeError("Database not initialized — call init_db() first")
        return _DBProxy._db[name]


db = _DBProxy()


def init_db(mongo_url: str, db_name: str):
    from motor.motor_asyncio import AsyncIOMotorClient
    _DBProxy._client = AsyncIOMotorClient(mongo_url)
    _DBProxy._db = _DBProxy._client[db_name]
    return db


def get_client():
    return _DBProxy._client
