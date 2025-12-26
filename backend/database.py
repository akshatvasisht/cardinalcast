"""Database session dependency for FastAPI."""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from backend.config import DB_URL

if DB_URL.startswith("postgresql"):
    engine = create_engine(DB_URL)
else:
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
