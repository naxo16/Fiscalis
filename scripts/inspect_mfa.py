import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.usuarios import Usuario, UsuarioMfa

async def inspect():
    async with AsyncSessionLocal() as session:
        users = (await session.scalars(select(Usuario))).all()
        for u in users:
            print(f"User: id={u.id}, username={u.username}, activo={u.activo}")
            mfa = (await session.scalars(select(UsuarioMfa).where(UsuarioMfa.usuario_id == u.id))).first()
            if mfa:
                print(f"  MFA: id={mfa.id}, enabled={mfa.enabled}, secret_enc={mfa.totp_secret_encrypted[:20]}...")
            else:
                print("  MFA: None")

if __name__ == "__main__":
    asyncio.run(inspect())
