import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings

_prod_engine = None
_prod_SessionLocal = None
_test_engine = None
_test_SessionLocal = None

def validate_database_urls():
    """
    Validates database connection urls to prevent testing against the production database.
    Raises ValueError if they are equal or missing.
    """
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL must be configured.")
    if not settings.TEST_DATABASE_URL:
        raise ValueError("TEST_DATABASE_URL must be configured.")
    if settings.DATABASE_URL.strip() == settings.TEST_DATABASE_URL.strip():
        raise ValueError(
            f"Database Safety Violation: DATABASE_URL and TEST_DATABASE_URL cannot be the same! "
            f"Value: '{settings.DATABASE_URL}'"
        )

def get_production_session() -> Session:
    """
    Returns a database session for the production database.
    """
    global _prod_engine, _prod_SessionLocal
    validate_database_urls()
    if _prod_SessionLocal is None:
        _prod_engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.LOG_LEVEL.upper() == "DEBUG"
        )
        _prod_SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_prod_engine
        )
    return _prod_SessionLocal()

def get_test_session() -> Session:
    """
    Returns a database session for the testing database.
    """
    global _test_engine, _test_SessionLocal
    validate_database_urls()
    if _test_SessionLocal is None:
        from sqlalchemy.pool import NullPool
        _test_engine = create_engine(
            settings.TEST_DATABASE_URL,
            echo=settings.LOG_LEVEL.upper() == "DEBUG",
            poolclass=NullPool
        )
        _test_SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_test_engine
        )
    return _test_SessionLocal()
