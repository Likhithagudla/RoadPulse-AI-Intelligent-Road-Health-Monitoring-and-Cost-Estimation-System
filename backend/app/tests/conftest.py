"""
RoadPulse AI - Pytest Test Configuration & Shared Fixtures
Configures isolated in-memory SQLite database, mock sessions, and authenticated clients.
"""

import os
import sys
import pytest
from pathlib import Path
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import SecurityService
from app.models.user import User
from app.main import app

# Isolated in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes tables in test database once per session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a transactional database session per test with automatic rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient that overrides get_db dependency with test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_users(db_session: Session):
    """Provisions admin, worker, and citizen user accounts into test db."""
    users = {
        "admin": User(
            username="test_admin",
            password_hash=SecurityService.get_password_hash("AdminPass123!"),
            role="admin",
            is_active=True,
        ),
        "worker": User(
            username="test_worker",
            password_hash=SecurityService.get_password_hash("WorkerPass123!"),
            role="worker",
            is_active=True,
        ),
        "user": User(
            username="test_user",
            password_hash=SecurityService.get_password_hash("UserPass123!"),
            role="user",
            is_active=True,
        ),
    }
    for u in users.values():
        db_session.add(u)
    db_session.commit()
    return users


@pytest.fixture
def admin_token(seeded_users) -> str:
    return SecurityService.create_access_token(
        data={"sub": seeded_users["admin"].username, "role": "admin"}
    )


@pytest.fixture
def worker_token(seeded_users) -> str:
    return SecurityService.create_access_token(
        data={"sub": seeded_users["worker"].username, "role": "worker"}
    )


@pytest.fixture
def user_token(seeded_users) -> str:
    return SecurityService.create_access_token(
        data={"sub": seeded_users["user"].username, "role": "user"}
    )
