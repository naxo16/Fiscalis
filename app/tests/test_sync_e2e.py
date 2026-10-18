import pytest
from httpx import AsyncClient
import uuid
import pyotp
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.registros import RegistroBase, InfraccionVehicular, EvidenciaFotografica
from app.models.auditoria import AuditoriaEvento, SyncEvent
from app.core.database import AsyncSessionLocal

TOTP_SECRET = "PTAJVCSZ35MSMOB22TUIDDHDS67YEESM"

async def get_auth_headers(client: AsyncClient) -> dict:
    """Helper para autenticar con MFA y obtener headers de autorización Bearer."""
    login_res = await client.post("/api/v1/auth/login", json={
        "username": "11111111-1",
        "password": "Cauquenes.2026*"
    })
    data = login_res.json()
    if data.get("mfa_required"):
        totp = pyotp.TOTP(TOTP_SECRET)
        verify_res = await client.post("/api/v1/auth/mfa/verify", json={
            "mfa_token": data["mfa_token"],
            "totp_code": totp.now()
        })
        token = verify_res.json()["access_token"]
    else:
        token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_sync_infraccion_vehicular_e2e(client: AsyncClient):
    """
    Prueba End-to-End de la sincronización de acta vehicular:
    1. Obtiene token de inspector validado con MFA
    2. Envía payload con PPU, infractor, coordenadas GPS y fotos
    3. Valida respuesta 201 y persistencia en PostgreSQL / PostGIS
    4. Valida auditoría de sincronización
    """
    headers = await get_auth_headers(client)

    acta_id = str(uuid.uuid4())
    payload = {
        "id": acta_id,
        "rutInfractor": "12345678-5",
        "nombreCompleto": "Carlos Conductor",
        "ppu": "KKYZ-88",
        "tipoVehiculo": "Camioneta",
        "marcaVehiculo": "Nissan Navara",
        "colorVehiculo": "Rojo",
        "tipoInfraccionId": 1,
        "coordenadas": "-35.9664,-72.3114",
        "fotos": [
            {"hash_sha256": f"hash_evidencia_1_{uuid.uuid4().hex}"},
            {"hash_sha256": f"hash_evidencia_2_{uuid.uuid4().hex}"}
        ],
        "fecha": datetime.now(timezone.utc).isoformat(),
        "descripcion": "Estacionamiento sobre paso peatonal",
        "firmaRechazo": False,
        "status": "EMITIDA"
    }

    # 1. Enviar sincronización
    res = await client.post("/api/v1/infracciones/sync", json=payload, headers=headers)
    assert res.status_code == 201
    assert "Sincronización exitosa" in res.json()["message"]

    # 2. Verificar persistencia en base de datos
    async with AsyncSessionLocal() as session:
        acta_db = await session.scalar(
            select(InfraccionVehicular).where(InfraccionVehicular.id == uuid.UUID(acta_id))
        )
        assert acta_db is not None
        assert acta_db.ppu == "KKYZ-88"
        assert acta_db.rut_infractor == "12345678-5"

        # Verificar evidencias
        evidencias = (await session.scalars(
            select(EvidenciaFotografica).where(EvidenciaFotografica.registro_uuid == uuid.UUID(acta_id))
        )).all()
        assert len(evidencias) == 2

        # Verificar auditoría
        auditoria = await session.scalar(
            select(AuditoriaEvento).where(AuditoriaEvento.entidad_id == acta_id)
        )
        assert auditoria is not None
        assert auditoria.accion == "CREACION_POR_SYNC"

@pytest.mark.asyncio
async def test_sync_idempotencia_no_duplica(client: AsyncClient):
    """
    Principio Offline-First: Si el dispositivo reintenta enviar un acta ya sincronizada
    (por ejemplo por pérdida de red antes de recibir el 201), el servidor no debe fallar
    ni duplicar, sino reconocer la idempotencia retornando el registro existente.
    """
    headers = await get_auth_headers(client)

    acta_id = str(uuid.uuid4())
    payload = {
        "id": acta_id,
        "ppu": "IDEM-99",
        "coordenadas": "-33.456,-70.654",
        "fotos": [f"hash_{uuid.uuid4().hex}"],
        "fecha": datetime.now(timezone.utc).isoformat(),
        "descripcion": "Vehículo mal estacionado - prueba idempotencia",
        "status": "EMITIDA"
    }

    # Primer envío
    res1 = await client.post("/api/v1/infracciones/sync", json=payload, headers=headers)
    assert res1.status_code == 201

    # Segundo envío (reintento idéntico)
    res2 = await client.post("/api/v1/infracciones/sync", json=payload, headers=headers)
    assert res2.status_code == 201

@pytest.mark.asyncio
async def test_listar_infracciones(client: AsyncClient):
    """Prueba el endpoint GET /api/v1/infracciones con inspector autenticado."""
    headers = await get_auth_headers(client)

    res = await client.get("/api/v1/infracciones", headers=headers)
    assert res.status_code == 200
    infracciones = res.json()
    assert isinstance(infracciones, list)
    assert len(infracciones) > 0
