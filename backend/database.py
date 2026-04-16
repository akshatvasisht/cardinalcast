"""Database session dependency for FastAPI."""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlmodel import Session

from backend.config import DB_URL

if DB_URL.startswith("postgresql"):
    engine = create_engine(DB_URL)
else:
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})


def SessionLocal() -> Session:
    """Return a new SQLModel Session (used by scheduler/lifecycle services)."""
    return Session(engine)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as db:
        yield db
