import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.usuarios import Usuario, Rol, DispositivoMovil, UsuarioMfa
from app.models.registros import RegistroBase, InfraccionVehicular, CatalogoInfraccion

async def main():
    async with AsyncSessionLocal() as session:
        # Check users
        users = (await session.scalars(select(Usuario))).all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f" - User: id={u.id}, username={u.username}, activo={u.activo}, rol_id={u.rol_id}")

        # Check devices
        devices = (await session.scalars(select(DispositivoMovil))).all()
        print(f"Total devices: {len(devices)}")
        for d in devices:
            print(f" - Device: id={d.id}, device_id={d.device_id}, revocado={d.revocado}, estado={d.estado}")

        # Check catalog
        catalog = (await session.scalars(select(CatalogoInfraccion))).all()
        print(f"Catalog items: {len(catalog)}")
        for c in catalog:
            print(f" - Infraccion {c.id}: {c.codigo_ley} - {c.descripcion} ({c.gravedad}, {c.costo_utm} UTM)")

        # Check infracciones
        infracciones = (await session.scalars(select(InfraccionVehicular))).all()
        print(f"Total Infracciones: {len(infracciones)}")
        for inf in infracciones:
            print(f" - Infraccion: id={inf.id}, ppu={inf.ppu}, estado={inf.estado}, fecha={inf.fecha_emision}")

if __name__ == "__main__":
    asyncio.run(main())
