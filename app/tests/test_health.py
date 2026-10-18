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
    assert data["database"] == "connected"
    assert "system" in data
    assert "version" in data

async def test_api_health_alias_returns_200(client: AsyncClient):
    """
    Test de infraestructura para monitores externos (UptimeRobot):
    /api/health y /api/v1/health responden 200 OK y ejecutan ping a base de datos.
    """
    res1 = await client.get("/api/health")
    assert res1.status_code == 200
    assert res1.json()["database"] == "connected"

    res2 = await client.get("/api/v1/health")
    assert res2.status_code == 200
    assert res2.json()["database"] == "connected"

async def test_health_check_db_failure_returns_500(client: AsyncClient, monkeypatch):
    """
    Simulación de contingencia para UptimeRobot:
    Si la base de datos no responde, el health check debe retornar 500 Internal Server Error.
    """
    from unittest.mock import AsyncMock, MagicMock
    from app import main

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(side_effect=Exception("Database connection timeout"))
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: mock_session)

    res = await client.get("/health")
    assert res.status_code == 500
    data = res.json()
    assert data["status"] == "error"
    assert data["database"] == "unreachable"
