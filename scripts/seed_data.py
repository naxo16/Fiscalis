import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal, engine
from app.models.base import Base
from app.models.usuarios import Usuario, Rol
from app.core.security import get_password_hash

async def seed_db():
    print("Iniciando proceso de seeder de base de datos...")
    
    print("[*] Limpiando dependencias antiguas y sincronizando nuevo esquema (Clean Architecture)...")
    async with engine.begin() as conn:
        # Usamos DROP CASCADE para eliminar dependencias viejas (como sesiones_moviles, registros)
        await conn.execute(text("DROP TABLE IF EXISTS usuarios CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS roles CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS registros_base CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS infracciones_vehiculares CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS evidencias_fotograficas CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS auditoria_eventos CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS sync_events CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS registros CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS vehiculos CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS evidencias CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS dispositivos CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS dispositivos_moviles CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS usuario_mfa CASCADE"))
        
        # Recreamos toda la arquitectura limpia
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        try:
            # 1. Verificar o crear el Rol "inspector" (RBAC)
            stmt_rol = select(Rol).where(Rol.nombre == "inspector")
            rol = await session.scalar(stmt_rol)
            
            if not rol:
                print("[*] Creando rol 'inspector'...")
                rol = Rol(nombre="inspector")
                session.add(rol)
                await session.flush() 
            else:
                print("[*] El rol 'inspector' ya existe en el sistema.")

            # 2. Verificar o crear el Usuario
            username = "11111111-1"
            stmt_user = select(Usuario).where(Usuario.username == username)
            user = await session.scalar(stmt_user)

            if not user:
                print(f"[*] Creando usuario '{username}'...")
                plain_password = "Cauquenes.2026*"
                
                # HASHEAMOS LA CONTRASEÑA USANDO BCRYPT
                hashed_password = get_password_hash(plain_password)
                
                nuevo_usuario = Usuario(
                    username=username,
                    hashed_password=hashed_password,
                    rol_id=rol.id,
                    activo=True
                )
                session.add(nuevo_usuario)
                await session.commit()
                await session.refresh(nuevo_usuario)
                user = nuevo_usuario
                print("[+] ¡Usuario creado exitosamente con credenciales seguras (bcrypt)!")
            else:
                print(f"[*] El usuario '{username}' ya existe.")

            # 3. Configurar Catálogo de Infracciones
            from app.models.registros import CatalogoInfraccion
            catalogo_items = [
                {"id": 1, "codigo_ley": "ADV", "descripcion": "Advertencia Empadronada Municipal", "gravedad": "LEVE", "costo_utm": 0.0},
                {"id": 2, "codigo_ley": "JPL", "descripcion": "Citación Juzgado de Policía Local (Art. 197 Ley 18.290)", "gravedad": "GRAVE", "costo_utm": 1.5},
                {"id": 3, "codigo_ley": "GRA", "descripcion": "Infracción Gravísima (Art. 198 Ley 18.290 - Conducción riesgosa / Semáforo)", "gravedad": "GRAVISIMA", "costo_utm": 3.0},
                {"id": 4, "codigo_ley": "MGRA", "descripcion": "Infracción Menos Grave (Art. 199 - Estacionamiento en sitio prohibido)", "gravedad": "MENOS_GRAVE", "costo_utm": 0.8},
                {"id": 5, "codigo_ley": "LEVE", "descripcion": "Infracción Leve (Art. 200 - Falta administrativa menor)", "gravedad": "LEVE", "costo_utm": 0.4},
                {"id": 6, "codigo_ley": "DISC", "descripcion": "Bloqueo de rampa o estacionamiento reservado para personas con discapacidad", "gravedad": "GRAVE", "costo_utm": 1.5},
                {"id": 7, "codigo_ley": "PARQ", "descripcion": "Evasión o no pago de parquímetro municipal en zona concesionada", "gravedad": "LEVE", "costo_utm": 0.5},
            ]
            for cat in catalogo_items:
                ex = await session.get(CatalogoInfraccion, cat["id"])
                if not ex:
                    session.add(CatalogoInfraccion(**cat))
            await session.commit()
            print("[+] Catálogo de infracciones inicializado con 7 tipos normativos.")

            # 4. Configurar Usuario MFA
            from datetime import datetime, timezone
            import uuid
            from app.models.usuarios import UsuarioMfa
            from app.api.endpoints.auth import encrypt_secret
            TOTP_SECRET_INSPECTOR = "PTAJVCSZ35MSMOB22TUIDDHDS67YEESM"
            
            stmt_mfa = select(UsuarioMfa).where(UsuarioMfa.usuario_id == user.id)
            mfa = await session.scalar(stmt_mfa)
            enc_secret = encrypt_secret(TOTP_SECRET_INSPECTOR)
            enc_recov = encrypt_secret("RECOV01,RECOV02,RECOV03,RECOV04")

            if not mfa:
                mfa = UsuarioMfa(
                    id=uuid.uuid4(),
                    usuario_id=user.id,
                    totp_secret_encrypted=enc_secret,
                    enabled=True,
                    confirmed_at=datetime.now(timezone.utc).isoformat(),
                    recovery_codes_encrypted=enc_recov
                )
                session.add(mfa)
            else:
                mfa.totp_secret_encrypted = enc_secret
                mfa.enabled = True
                mfa.confirmed_at = datetime.now(timezone.utc).isoformat()
                mfa.recovery_codes_encrypted = enc_recov
            await session.commit()
            print("[+] MFA inicializado y habilitado para inspector de pruebas.")

        except Exception as e:
            await session.rollback()
            print(f"[!] Error durante la ejecución del seeder: {e}")

if __name__ == "__main__":
    asyncio.run(seed_db())
