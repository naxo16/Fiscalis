# app/tests/test_infracciones.py
import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone

from app.main import app
from app.api.deps import get_current_inspector, get_db

# --- MOCKS (Simuladores de Dependencias) ---

MOCK_INSPECTOR_ID = uuid.UUID("fa095a27-4e47-4099-b6a4-f4bd34650fbc")

async def mock_get_current_inspector():
    """Simula un inspector autenticado en terreno"""
    return MOCK_INSPECTOR_ID

class MockFailingSession:
    """Simulador de una conexión de SQLAlchemy que colapsa"""
    async def scalar(self, *args, **kwargs):
        raise Exception("Critical: Connection timeout to PostgreSQL cluster on 5432")
    async def execute(self, *args, **kwargs):
        raise Exception("Critical: Connection timeout to PostgreSQL cluster on 5432")
    async def rollback(self, *args, **kwargs):
        pass

async def mock_get_db_con_falla():
    """Inyecta el fallo de base de datos al Router"""
    yield MockFailingSession()

# --- UTILIDAD: Payload Base Válido (Contrato SGF SincronizacionActaRequest) ---
def generar_payload_valido():
    return {
        "id": str(uuid.uuid4()),
        "rutInfractor": "11111111-1",
        "nombreCompleto": "Juan Perez",
        "ppu": "BBCL-12",
        "tipoVehiculo": "Automovil",
        "marcaVehiculo": "Toyota",
        "colorVehiculo": "Gris",
        "tipoInfraccionId": 1,
        "coordenadas": "-33.4569,-70.6482",
        "fotos": ["hash_sha256_mock_abc123"],
        "fecha": datetime.now(timezone.utc).isoformat(),
        "descripcion": "Estacionado en lugar no permitido según Ordenanza Municipal",
        "firmaRechazo": False,
        "status": "EMITIDA"
    }

# --- CASOS DE PRUEBA DE RESILIENCIA ---

async def test_sync_sin_token_rechaza_401(client: AsyncClient):
    """
    SGI-IT-01: Dispositivo sin token o expirado.
    Debe responder 401 para que el móvil detenga la cola y pida re-autenticación.
    """
    app.dependency_overrides = {}  # Limpiamos overrides previos
    payload = generar_payload_valido()
    
    response = await client.post("/api/v1/infracciones/sync", json=payload)
    
    assert response.status_code == 401

async def test_sync_payload_corrupto_rechaza_422(client: AsyncClient):
    """
    SGI-UT-01: Datos corruptos desde terreno (Falta coordenadas obligatorias).
    Debe responder 422 para que el móvil marque el registro como inválido y NO reintente infinitamente.
    """
    app.dependency_overrides[get_current_inspector] = mock_get_current_inspector
    
    payload_invalido = generar_payload_valido()
    del payload_invalido["coordenadas"]  # Quitamos campo obligatorio
    
    response = await client.post("/api/v1/infracciones/sync", json=payload_invalido)
    
    assert response.status_code == 422
    assert "coordenadas" in response.text
    
    app.dependency_overrides = {}

async def test_sync_falla_servidor_gatilla_backoff_500(client: AsyncClient):
    """
    SGI-IT-02: Error sistémico interno (BD inalcanzable).
    Debe responder 500 estructurado para gatillar el Backoff Exponencial en Flutter.
    """
    app.dependency_overrides[get_current_inspector] = mock_get_current_inspector
    app.dependency_overrides[get_db] = mock_get_db_con_falla
    
    payload = generar_payload_valido()
    response = await client.post("/api/v1/infracciones/sync", json=payload)
    
    assert response.status_code == 500
    assert "Exponential Backoff" in response.json()["detail"]
    
    app.dependency_overrides = {}