"""
Database setup, connection lifecycle, and migration helpers for SQLite.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.models import Base

DATABASE_PATH = os.environ.get("KIVI_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "kivi_memory.db"))
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Creates tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Drops all tables and recreates them cleanly."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
