# app/tests/test_cors_flutter_web.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_cors_preflight_flutter_web_port(client: AsyncClient):
    """
    QA Test: Simula la petición Preflight (OPTIONS) que realiza Flutter Web
    desde un puerto diferente (ej: http://localhost:1859).
    Verifica que el backend retorne 200 con encabezados CORS válidos.
    """
    headers = {
        "Origin": "http://localhost:1859",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type"
    }
    
    response = await client.options("/api/v1/auth/login", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:1859"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")

@pytest.mark.asyncio
async def test_cors_preflight_127_0_0_1_port(client: AsyncClient):
    """
    QA Test: Simula Flutter Web accediendo desde 127.0.0.1 en cualquier puerto.
    """
    headers = {
        "Origin": "http://127.0.0.1:1859",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type"
    }
    
    response = await client.options("/api/v1/infracciones/sync", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:1859"
    assert response.headers.get("access-control-allow-credentials") == "true"

@pytest.mark.asyncio
async def test_cors_preflight_arbitrary_flutter_port(client: AsyncClient):
    """
    QA Test: Simula Flutter Web levantado dinámicamente en cualquier otro puerto (ej: 54321).
    """
    headers = {
        "Origin": "http://localhost:54321",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization"
    }
    
    response = await client.options("/api/v1/infracciones", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:54321"

@pytest.mark.asyncio
async def test_cors_post_request_includes_corp_header(client: AsyncClient):
    """
    QA Test: Verifica que peticiones reales desde Flutter Web reciban
    Access-Control-Allow-Origin y Cross-Origin-Resource-Policy.
    """
    headers = {
        "Origin": "http://localhost:1859",
        "Content-Type": "application/json"
    }
    response = await client.post("/api/v1/auth/login", json={
        "username": "usuario_prueba_inexistente",
        "password": "PasswordInvalida123"
    }, headers=headers)
    
    # Aunque retorne 401 por credenciales incorrectas, los headers CORS deben estar presentes
    assert response.headers.get("access-control-allow-origin") == "http://localhost:1859"
    assert response.headers.get("cross-origin-resource-policy") == "cross-origin"
