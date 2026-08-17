import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session")
def client():
    """
    Session-scoped TestClient that triggers FastAPI lifespan (model loading & warmup) once.
    """
    with TestClient(app) as test_client:
        yield test_client
