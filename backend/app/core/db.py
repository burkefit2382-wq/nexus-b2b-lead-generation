from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings


_engine: Engine | None = None
_session_local: sessionmaker[Session] | None = None


def sqlalchemy_database_url() -> str:
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        database_url = sqlalchemy_database_url()
        if not database_url:
            raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
        _engine = create_engine(database_url, pool_pre_ping=True)
    return _engine


def get_session_local() -> sessionmaker[Session]:
    global _session_local
    if _session_local is None:
        _session_local = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_local


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
