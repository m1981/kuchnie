# tests/conftest.py
import pytest
from sqlmodel import SQLModel, Session, create_engine
from kitchen_erp.database import get_session

@pytest.fixture(name="session")
def session_fixture():
    """Provides an in-memory SQLite database session for tests."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session