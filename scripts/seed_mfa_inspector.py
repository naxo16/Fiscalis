import asyncio
import os
import sys
from datetime import datetime, timezone
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.usuarios import Usuario, UsuarioMfa
from app.api.endpoints.auth import encrypt_secret

TOTP_SECRET_INSPECTOR = "PTAJVCSZ35MSMOB22TUIDDHDS67YEESM"

async def seed_mfa():
    async with AsyncSessionLocal() as session:
        user = (await session.scalars(select(Usuario).where(Usuario.username == "11111111-1"))).first()
        if not user:
            print("Usuario 11111111-1 no encontrado!")
            return

        mfa = (await session.scalars(select(UsuarioMfa).where(UsuarioMfa.usuario_id == user.id))).first()
        enc_secret = encrypt_secret(TOTP_SECRET_INSPECTOR)
        enc_recov = encrypt_secret("RECOV01,RECOV02,RECOV03,RECOV04")

        if mfa:
            print(f"Actualizando MFA existente para {user.username}...")
            mfa.totp_secret_encrypted = enc_secret
            mfa.enabled = True
            mfa.confirmed_at = datetime.now(timezone.utc).isoformat()
            mfa.recovery_codes_encrypted = enc_recov
        else:
            print(f"Creando nuevo registro MFA para {user.username}...")
            mfa = UsuarioMfa(
                id=uuid.uuid4(),
                usuario_id=user.id,
                totp_secret_encrypted=enc_secret,
                enabled=True,
                confirmed_at=datetime.now(timezone.utc).isoformat(),
                recovery_codes_encrypted=enc_recov
            )
            session.add(mfa)
        
        await session.commit()
        print(f"[+] MFA configurado y activado exitosamente para {user.username} con clave TOTP conocida.")

if __name__ == "__main__":
    asyncio.run(seed_mfa())
