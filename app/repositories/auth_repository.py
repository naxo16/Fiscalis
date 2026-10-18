from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usuarios import Usuario

class AuthRepository:
    """
    Repositorio encargado de las consultas a la base de datos relacionadas
    con la autenticación y usuarios.
    """
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Usuario | None:
        """
        Obtiene un usuario a partir de su username utilizando sintaxis moderna de SQLAlchemy 2.0.
        """
        stmt = select(Usuario).where(Usuario.username == username)
        return await db.scalar(stmt)

    async def get_user_mfa(self, db: AsyncSession, usuario_id) -> "UsuarioMfa | None":
        from app.models.usuarios import UsuarioMfa
        stmt = select(UsuarioMfa).where(UsuarioMfa.usuario_id == usuario_id)
        return await db.scalar(stmt)

    async def create_user_mfa(self, db: AsyncSession, usuario_id, secret: str) -> "UsuarioMfa":
        from app.models.usuarios import UsuarioMfa
        import uuid
        mfa = UsuarioMfa(id=uuid.uuid4(), usuario_id=usuario_id, totp_secret_encrypted=secret)
        db.add(mfa)
        await db.commit()
        await db.refresh(mfa)
        return mfa

    async def update_user_mfa_enabled(self, db: AsyncSession, mfa, enabled: bool):
        mfa.enabled = enabled
        mfa.confirmed_at = datetime.now(timezone.utc).isoformat()
        await db.commit()

    async def upsert_device(self, db: AsyncSession, usuario_id, device_id: str) -> "DispositivoMovil":
        from app.models.usuarios import DispositivoMovil
        import uuid
        stmt = select(DispositivoMovil).where(DispositivoMovil.device_id == device_id)
        dev = await db.scalar(stmt)
        if dev:
            dev.usuario_id = usuario_id
            dev.last_seen_at = datetime.now(timezone.utc).isoformat()
            await db.commit()
            return dev
        
        dev = DispositivoMovil(
            id=uuid.uuid4(),
            usuario_id=usuario_id,
            device_id=device_id,
            last_seen_at=datetime.now(timezone.utc).isoformat()
        )
        db.add(dev)
        await db.commit()
        await db.refresh(dev)
        return dev

    async def get_device(self, db: AsyncSession, device_id: str) -> "DispositivoMovil | None":
        from app.models.usuarios import DispositivoMovil
        stmt = select(DispositivoMovil).where(DispositivoMovil.device_id == device_id)
        return await db.scalar(stmt)
