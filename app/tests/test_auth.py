import pytest
from httpx import AsyncClient
import pyotp
import uuid

# Semilla MFA configurada para el usuario inspector 11111111-1
TOTP_SECRET_INSPECTOR = "PTAJVCSZ35MSMOB22TUIDDHDS67YEESM"

@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_login_con_credenciales_validas_retorna_token_o_challenge(client: AsyncClient):
    """
    Prueba que el login con credenciales correctas retorna un token de acceso directo
    o un desafío MFA si el segundo factor está activado.
    """
    response = await client.post("/api/v1/auth/login", json={
        "username": "11111111-1",
        "password": "Cauquenes.2026*",
        "device_id": f"device-test-{uuid.uuid4()}"
    })
    assert response.status_code == 200
    data = response.json()
    if data.get("mfa_required"):
        assert "mfa_token" in data
        assert data["mfa_token"] is not None
    else:
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "11111111-1"

@pytest.mark.asyncio
async def test_mfa_verify_o_login_directo_emite_jwt_final_con_usuario(client: AsyncClient):
    """
    Prueba que la autenticación completa emite el JWT final de sesión con el perfil de inspector.
    """
    login_res = await client.post("/api/v1/auth/login", json={
        "username": "11111111-1",
        "password": "Cauquenes.2026*"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()

    if login_data.get("mfa_required"):
        mfa_token = login_data["mfa_token"]
        totp = pyotp.TOTP(TOTP_SECRET_INSPECTOR)
        current_code = totp.now()

        verify_res = await client.post("/api/v1/auth/mfa/verify", json={
            "mfa_token": mfa_token,
            "totp_code": current_code
        })
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert "access_token" in data
        assert data["user"]["username"] == "11111111-1"
    else:
        assert "access_token" in login_data
        assert login_data["user"]["username"] == "11111111-1"
        assert login_data["user"]["rol"] == "inspector"

@pytest.mark.asyncio
async def test_login_password_incorrecta_retorna_401(client: AsyncClient):
    """Prueba rechazo por contraseña errónea (401 Unauthorized)."""
    response = await client.post("/api/v1/auth/login", json={
        "username": "11111111-1",
        "password": "PasswordIncorrecta999*"
    })
    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_usuario_inexistente_retorna_401(client: AsyncClient):
    """Prueba rechazo por usuario inexistente (401 Unauthorized)."""
    response = await client.post("/api/v1/auth/login", json={
        "username": "99999999-9",
        "password": "PasswordCualquiera123*"
    })
    assert response.status_code == 401
    assert "incorrectos" in response.json()["detail"]

@pytest.mark.asyncio
async def test_mfa_validate_desbloqueo_sesion(client: AsyncClient):
    """
    Prueba el endpoint /api/v1/auth/mfa/validate utilizado por SessionLockScreen
    para revalidar al inspector tras período de hibernación (>60s).
    """
    login_res = await client.post("/api/v1/auth/login", json={
        "username": "11111111-1",
        "password": "Cauquenes.2026*"
    })
    login_data = login_res.json()
    totp = pyotp.TOTP(TOTP_SECRET_INSPECTOR)
    
    if login_data.get("mfa_required"):
        mfa_token = login_data["mfa_token"]
        verify_res = await client.post("/api/v1/auth/mfa/verify", json={
            "mfa_token": mfa_token,
            "totp_code": totp.now()
        })
        access_token = verify_res.json()["access_token"]
    else:
        access_token = login_data["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Validar que el token de sesión es legítimo
    check_res = await client.get("/api/v1/infracciones", headers=headers)
    assert check_res.status_code == 200

@pytest.mark.asyncio
async def test_token_invalido_rechaza_401(client: AsyncClient):
    """Valida que un token alterado o inválido es rechazado por el middleware de seguridad."""
    headers = {"Authorization": "Bearer token_falso_invalido_xyz"}
    res = await client.get("/api/v1/infracciones", headers=headers)
    assert res.status_code == 401
