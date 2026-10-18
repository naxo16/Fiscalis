# app/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client() -> AsyncClient:
    """
    Cliente de pruebas asíncrono de FastAPI.
    El transport ASGITransport procesa las peticiones en memoria sin levantar sockets reales.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://testserver"
    ) as ac:
        yield ac

@pytest.fixture(scope="session", autouse=True)
async def cleanup_engine():
    yield
    await engine.dispose()