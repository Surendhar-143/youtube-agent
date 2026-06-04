import os
import sys
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from config.settings import settings
from database.session_factory import validate_database_urls

# Detect if we are running in a unit test environment
is_testing = (
    "unittest" in sys.modules or
    "pytest" in sys.modules or
    os.environ.get("APP_ENV") == "test" or
    os.environ.get("YACE_ENV") == "test"
)

# Enforce safety check on urls
validate_database_urls()

if is_testing:
    db_url = settings.TEST_DATABASE_URL
else:
    db_url = settings.DATABASE_URL

# Create engine
if is_testing:
    from sqlalchemy.pool import NullPool
    engine = create_engine(
        db_url,
        echo=settings.LOG_LEVEL.upper() == "DEBUG",
        poolclass=NullPool
    )
else:
    engine = create_engine(
        db_url,
        echo=settings.LOG_LEVEL.upper() == "DEBUG"
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base model class
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass

# Dependency generator
def get_db() -> Generator[Session, None, None]:
    """
    SQLAlchemy database session generator.
    Yields a session and closes it when complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
