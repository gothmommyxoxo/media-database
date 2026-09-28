import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db, make_engine
from app.main import app


@pytest.fixture()
def db_session():
    """An isolated database per test: in-memory SQLite by default, or real MySQL when
    TEST_DATABASE_URL is set.

    The full spec (10.2) calls for integration tests against a real MySQL database to catch
    MySQL-specific behavior (e.g. JSON column semantics). SQLite keeps the default run fast and
    dependency-free; scripts/test-mysql.sh runs the same suite against a throwaway MySQL 8.0
    container. The schema is created and dropped around every test, so point TEST_DATABASE_URL
    only at a disposable database.
    """
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    if test_database_url:
        engine = make_engine(test_database_url)
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
