import pytest
from httpx import AsyncClient

async def test_health_check_returns_200(client: AsyncClient):
    """
    Test de infraestructura: El endpoint de health check responde 200 OK
    con el nombre del proyecto y versión.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "system" in data
    assert "version" in data
