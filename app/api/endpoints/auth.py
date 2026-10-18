from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import pyotp

from app.api.deps import get_db, get_current_inspector
from app.repositories.auth_repository import AuthRepository
from app.core.security import create_access_token, verify_password
from app.schemas.auth import (
    TokenResponse, LoginRequest, MfaVerifyRequest, 
    MfaSetupResponse, MfaConfirmRequest, MfaSetupRequest
)

router = APIRouter()
auth_repo = AuthRepository()

# Utilidad para cifrar/descifrar TOTP secret usando Fernet con soporte para rotación de claves
from cryptography.fernet import Fernet, MultiFernet
import os
import base64
import hashlib
from app.core.config import settings
from app.core.security import SECRET_KEY

# Clave primaria derivada de configuración
h_primary = hashlib.sha256(SECRET_KEY.encode()).digest()
primary_key = settings.MFA_ENCRYPTION_KEY or base64.urlsafe_b64encode(h_primary).decode()

# Clave heredada para soporte de rotación sin invalidar datos existentes
legacy_key = base64.urlsafe_b64encode(hashlib.sha256(b"fiscalis_mvp_key").digest()).decode()

keys = [Fernet(primary_key)]
if legacy_key != primary_key:
    keys.append(Fernet(legacy_key))

fernet = MultiFernet(keys)

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()

@router.post("/login", response_model=TokenResponse)
async def login_for_access_token(
    request_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await auth_repo.get_user_by_username(db, username=request_data.username)
    
    # OWASP A07: Mitigación de User Enumeration mediante Timing Attack
    if not user:
        verify_password(request_data.password, "$2b$12$e86XoX2JcR4N9mQ0sZ3W3O8h3v1n1f8K4J8L9P0Q1R2S3T4U5V6W7")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(request_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo o revocado por administración institucional",
        )
    
    # Device Binding (si se provee)
    if request_data.device_id:
        dev = await auth_repo.get_device(db, request_data.device_id)
        if dev and dev.revocado:
            raise HTTPException(status_code=403, detail="Dispositivo revocado por polÃ­tica institucional")
        await auth_repo.upsert_device(db, user.id, request_data.device_id)

    # Validar MFA
    mfa = await auth_repo.get_user_mfa(db, user.id)
    if mfa and mfa.enabled:
        # Emitir token temporal para verificar MFA
        mfa_token = create_access_token(data={"sub": str(user.id), "scopes": ["mfa_pending"]}, expires_delta_minutes=5)
        return TokenResponse(
            mfa_required=True,
            mfa_token=mfa_token,
            expires_in=300
        )
    
    # Sin MFA
    access_token = create_access_token(data={"sub": str(user.id), "scopes": ["access"], "device_id": request_data.device_id})
    return TokenResponse(
        access_token=access_token, 
        token_type="bearer",
        expires_in=28800,
        user={"id": str(user.id), "username": user.username, "rol": "inspector"}
    )

@router.post("/mfa/verify", response_model=TokenResponse)
async def mfa_verify(
    request_data: MfaVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    import jwt
    from jwt.exceptions import InvalidTokenError
    from app.core.security import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(request_data.mfa_token, SECRET_KEY, algorithms=[ALGORITHM])
        import uuid
        user_id = uuid.UUID(payload.get("sub"))
        scopes = payload.get("scopes", [])
        if "mfa_pending" not in scopes:
            raise HTTPException(status_code=401, detail="Token no válido para verificación MFA")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token MFA inválido o expirado")
    
    mfa = await auth_repo.get_user_mfa(db, user_id)
    if not mfa or not mfa.enabled:
        raise HTTPException(status_code=400, detail="MFA no esta habilitado")

    # LÃ³gica de verificaciÃ³n: TOTP o CÃ³digo de RecuperaciÃ³n
    if request_data.recovery_code:
        # RecuperaciÃ³n
        if not mfa.recovery_codes_encrypted:
            raise HTTPException(status_code=400, detail="No hay cÃ³digos de recuperaciÃ³n disponibles")
        
        recovery_codes_str = decrypt_secret(mfa.recovery_codes_encrypted)
        recovery_codes = recovery_codes_str.split(',') if recovery_codes_str else []
        
        if request_data.recovery_code not in recovery_codes:
            raise HTTPException(status_code=401, detail="CÃ³digo de recuperaciÃ³n invÃ¡lido o ya utilizado")
            
        # Consumir el cÃ³digo
        recovery_codes.remove(request_data.recovery_code)
        mfa.recovery_codes_encrypted = encrypt_secret(",".join(recovery_codes))
        await db.commit()
        
        # AuditorÃ­a uso de recuperaciÃ³n
        from app.models.auditoria import AuditoriaEvento
        db.add(AuditoriaEvento(
            entidad_id=str(user_id), entidad_tipo="UsuarioMfa", accion="MFA_RECUPERACION_USADA",
            usuario_id=user_id, payload={"restantes": len(recovery_codes)}
        ))
        await db.commit()
    else:
        # TOTP normal
        if not request_data.totp_code:
            raise HTTPException(status_code=400, detail="Debe proveer un cÃ³digo TOTP o un cÃ³digo de recuperaciÃ³n")
            
        secret = decrypt_secret(mfa.totp_secret_encrypted)
        totp = pyotp.TOTP(secret)
        if not totp.verify(request_data.totp_code, valid_window=2):
            raise HTTPException(status_code=401, detail="CÃ³digo TOTP incorrecto")

    # Si proporcionÃ³ device id, verificarlo
    if request_data.device_id:
        dev = await auth_repo.get_device(db, request_data.device_id)
        if dev and dev.revocado:
            raise HTTPException(status_code=403, detail="Dispositivo revocado por polÃ­tica institucional")
        await auth_repo.upsert_device(db, user_id, request_data.device_id)

    from app.models.usuarios import Usuario
    from sqlalchemy import select
    import uuid
    user = await db.scalar(select(Usuario).where(Usuario.id == user_id))

    access_token = create_access_token(data={"sub": str(user_id), "scopes": ["access"], "device_id": request_data.device_id})
    return TokenResponse(
        access_token=access_token, 
        token_type="bearer",
        expires_in=28800,
        user={"id": str(user_id), "username": user.username if user else "", "rol": "inspector"}
    )

@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    request_data: MfaSetupRequest,
    current_user_id = Depends(get_current_inspector),
    db: AsyncSession = Depends(get_db)
):
    from app.models.usuarios import Usuario
    from sqlalchemy import select
    import secrets
    import string
    
    # 1. Validar contraseÃ±a reciente
    user = await db.scalar(select(Usuario).where(Usuario.id == current_user_id))
    if not user or not verify_password(request_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="ContraseÃ±a incorrecta. Se requiere confirmaciÃ³n para activar MFA.")

    mfa = await auth_repo.get_user_mfa(db, current_user_id)
    if mfa and mfa.enabled:
        raise HTTPException(status_code=400, detail="MFA ya esta habilitado. No se puede generar una nueva semilla.")

    if mfa and not mfa.enabled:
        try:
            secret = decrypt_secret(mfa.totp_secret_encrypted)
            if not mfa.recovery_codes_encrypted:
                raise ValueError("Faltan cÃ³digos de recuperaciÃ³n")
            recovery_codes_str = decrypt_secret(mfa.recovery_codes_encrypted)
            recovery_codes = recovery_codes_str.split(',')
        except Exception:
            # Clave de encriptaciÃ³n rotada o datos corruptos, regenerar
            secret = pyotp.random_base32()
            recovery_codes = [''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)) for _ in range(8)]
            recovery_codes_str = ",".join(recovery_codes)
            mfa.totp_secret_encrypted = encrypt_secret(secret)
            mfa.recovery_codes_encrypted = encrypt_secret(recovery_codes_str)
            await db.commit()
    else:
        # 2. Generar TOTP Secret y CÃ³digos de RecuperaciÃ³n nuevos
        secret = pyotp.random_base32()
        recovery_codes = [''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8)) for _ in range(8)]
        recovery_codes_str = ",".join(recovery_codes)
        
        mfa = await auth_repo.create_user_mfa(db, current_user_id, encrypt_secret(secret))
        mfa.recovery_codes_encrypted = encrypt_secret(recovery_codes_str)
        await db.commit()

    # 4. AuditorÃ­a
    from app.models.auditoria import AuditoriaEvento
    auditoria = AuditoriaEvento(
        entidad_id=str(current_user_id),
        entidad_tipo="UsuarioMfa",
        accion="MFA_SETUP_INICIADO",
        usuario_id=current_user_id,
        payload={"message": "IniciÃ³ configuraciÃ³n de MFA"}
    )
    db.add(auditoria)
    await db.commit()

    otp_auth_url = pyotp.TOTP(secret).provisioning_uri(
        name=user.username,
        issuer_name="Fiscalis"
    )

    return MfaSetupResponse(
        otp_auth_url=otp_auth_url,
        manual_secret=secret,
        recovery_codes=recovery_codes
    )

@router.post("/mfa/confirm")
async def confirm_mfa(
    request_data: MfaConfirmRequest,
    current_user_id = Depends(get_current_inspector),
    db: AsyncSession = Depends(get_db)
):
    mfa = await auth_repo.get_user_mfa(db, current_user_id)
    if not mfa or mfa.enabled:
        raise HTTPException(status_code=400, detail="MFA no esta en proceso de configuraciÃ³n")

    secret = decrypt_secret(mfa.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)
    if not totp.verify(request_data.totp_code, valid_window=2):
        raise HTTPException(status_code=401, detail="CÃ³digo TOTP incorrecto")

    await auth_repo.update_user_mfa_enabled(db, mfa, True)
    
    # 3. AuditorÃ­a
    from app.models.auditoria import AuditoriaEvento
    db.add(AuditoriaEvento(
        entidad_id=str(current_user_id),
        entidad_tipo="UsuarioMfa",
        accion="MFA_ACTIVADO",
        usuario_id=current_user_id,
        payload={"message": "MFA confirmado y activado exitosamente"}
    ))
    await db.commit()
    
    return {"message": "MFA habilitado correctamente"}
@router.post("/mfa/validate")
async def validate_mfa(
    request_data: MfaConfirmRequest,
    current_user_id = Depends(get_current_inspector),
    db: AsyncSession = Depends(get_db)
):
    mfa = await auth_repo.get_user_mfa(db, current_user_id)
    if not mfa or not mfa.enabled:
        raise HTTPException(status_code=400, detail="MFA no esta habilitado")

    secret = decrypt_secret(mfa.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)
    if not totp.verify(request_data.totp_code, valid_window=2):
        raise HTTPException(status_code=401, detail="Código TOTP incorrecto")
        
    return {"status": "success"}

@router.post("/mfa/revoke")
async def revoke_mfa(
    request_data: MfaConfirmRequest,
    current_user_id = Depends(get_current_inspector),
    db: AsyncSession = Depends(get_db)
):
    mfa = await auth_repo.get_user_mfa(db, current_user_id)
    if not mfa or not mfa.enabled:
        raise HTTPException(status_code=400, detail="MFA no esta habilitado")

    import pyotp
    secret = decrypt_secret(mfa.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)
    if not totp.verify(request_data.totp_code, valid_window=2):
        raise HTTPException(status_code=401, detail="Código TOTP incorrecto")

    await db.delete(mfa)
    
    from app.models.auditoria import AuditoriaEvento
    db.add(AuditoriaEvento(
        entidad_id=str(current_user_id),
        entidad_tipo="UsuarioMfa",
        accion="MFA_REVOCADO",
        usuario_id=current_user_id,
        payload={"message": "MFA revocado por el usuario"}
    ))
    await db.commit()
    
    return {"message": "MFA revocado correctamente"}
