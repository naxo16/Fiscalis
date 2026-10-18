import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.registros import CatalogoInfraccion

CATALOGO_ITEMS = [
    {"id": 1, "codigo_ley": "ADV", "descripcion": "Advertencia Empadronada Municipal", "gravedad": "LEVE", "costo_utm": 0.0},
    {"id": 2, "codigo_ley": "JPL", "descripcion": "Citación Juzgado de Policía Local (Art. 197 Ley 18.290)", "gravedad": "GRAVE", "costo_utm": 1.5},
    {"id": 3, "codigo_ley": "GRA", "descripcion": "Infracción Gravísima (Art. 198 Ley 18.290 - Conducción riesgosa / Semáforo)", "gravedad": "GRAVISIMA", "costo_utm": 3.0},
    {"id": 4, "codigo_ley": "MGRA", "descripcion": "Infracción Menos Grave (Art. 199 - Estacionamiento en sitio prohibido)", "gravedad": "MENOS_GRAVE", "costo_utm": 0.8},
    {"id": 5, "codigo_ley": "LEVE", "descripcion": "Infracción Leve (Art. 200 - Falta administrativa menor)", "gravedad": "LEVE", "costo_utm": 0.4},
    {"id": 6, "codigo_ley": "DISC", "descripcion": "Bloqueo de rampa o estacionamiento reservado para personas con discapacidad", "gravedad": "GRAVE", "costo_utm": 1.5},
    {"id": 7, "codigo_ley": "PARQ", "descripcion": "Evasión o no pago de parquímetro municipal en zona concesionada", "gravedad": "LEVE", "costo_utm": 0.5},
]

async def seed_catalogo():
    async with AsyncSessionLocal() as session:
        for item in CATALOGO_ITEMS:
            existing = await session.get(CatalogoInfraccion, item["id"])
            if existing:
                existing.codigo_ley = item["codigo_ley"]
                existing.descripcion = item["descripcion"]
                existing.gravedad = item["gravedad"]
                existing.costo_utm = item["costo_utm"]
                print(f"Actualizado ítem {item['id']}: {item['codigo_ley']}")
            else:
                nuevo = CatalogoInfraccion(**item)
                session.add(nuevo)
                print(f"Insertado nuevo ítem {item['id']}: {item['codigo_ley']}")
        await session.commit()
        print("[+] Catálogo de infracciones actualizado exitosamente.")

if __name__ == "__main__":
    asyncio.run(seed_catalogo())
