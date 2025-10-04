"""Database session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLSession

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://telemetry:telemetry_dev_password@localhost:5432/pr_telemetry"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> SQLSession:
    """
    Dependency for FastAPI routes to get a database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

