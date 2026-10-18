# -*- coding: utf-8 -*-
"""
Script de Verificación y Carga de Calidad (QA):
1. Autentica contra la API activa (/api/v1/auth/login).
2. Genera y transmite más de 150 actas de infracción vehicular (/api/v1/infracciones/sync).
3. Prueba la resiliencia, concurrencia, validación y persistencia PostGIS en PostgreSQL.
4. Verifica la lectura vía API (/api/v1/infracciones) y conteo directo en base de datos.
"""
import asyncio
import os
import sys
import uuid
import random
import hashlib
from datetime import datetime, timedelta, timezone
import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TOTAL_REGISTROS = 160
CONCURRENCY_LIMIT = 8

NOMBRES = ["Juan", "Carlos", "José", "Luis", "Manuel", "Jorge", "Cristian", "Rodrigo", "María", "Patricia", "Claudia", "Camila", "Daniela", "Constanza", "Francisca"]
APELLIDOS = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Morales", "López", "Fuentes", "Valenzuela", "Araya", "Sepúlveda", "Castillo"]
MARCAS_MODELOS = [
    ("Toyota", "Hilux", "Camioneta"),
    ("Nissan", "Versa", "Automóvil"),
    ("Chevrolet", "D-Max", "Camioneta"),
    ("Hyundai", "Accent", "Automóvil"),
    ("Kia", "Rio", "Automóvil"),
    ("Peugeot", "208", "Automóvil"),
    ("Ford", "Ranger", "Camioneta"),
    ("Mitsubishi", "L200", "Camioneta"),
    ("Suzuki", "Swift", "Automóvil"),
    ("Volkswagen", "Gol", "Automóvil"),
    ("Honda", "CB190R", "Motocicleta"),
    ("Yamaha", "FZ-S", "Motocicleta"),
    ("Mercedes-Benz", "Sprinter", "Furgón"),
    ("Hyundai", "Tucson", "SUV"),
    ("Nissan", "Kicks", "SUV")
]
COLORES = ["Blanco", "Gris Plata", "Negro", "Rojo", "Azul Marino", "Verde", "Dorado", "Gris Oscuro"]
DESCRIPCIONES = [
    "Estacionado sobre vereda o paso peatonal señalizado según Ley de Tránsito.",
    "Vehículo bloqueando acceso a garaje particular debidamente señalizado.",
    "Estacionar en ochava / esquina impidiendo la visibilidad en intersección.",
    "Estacionamiento en zona reservada para carga y descarga fuera del horario permitido.",
    "Sin ticket ni acreditación de cobro de parquímetro municipal en sector céntrico.",
    "Bloqueo directo de rampa y acceso habilitado para personas con discapacidad.",
    "Estacionar frente a grifo de incendio a menos de 5 metros.",
    "Vehículo en doble fila obstaculizando el tránsito vehicular en calle Victoria."
]

def calcular_dv(rut_sin_dv: int) -> str:
    """Calcula el dígito verificador módulo 11 de un RUT chileno."""
    multiplicadores = [2, 3, 4, 5, 6, 7]
    suma = 0
    rut_str = str(rut_sin_dv)[::-1]
    for i, char in enumerate(rut_str):
        suma += int(char) * multiplicadores[i % len(multiplicadores)]
    resto = 11 - (suma % 11)
    if resto == 11:
        return '0'
    elif resto == 10:
        return 'K'
    else:
        return str(resto)

def generar_rut_chileno() -> str:
    num = random.randint(7000000, 24000000)
    dv = calcular_dv(num)
    return f"{num}-{dv}"

def generar_ppu_chilena() -> str:
    letras = "".join(random.choices("BCDFGHJKLPRSTVWXYZ", k=4))
    numeros = f"{random.randint(10, 99):02d}"
    return f"{letras}-{numeros}"

async def autenticar(client: httpx.AsyncClient) -> str:
    """Inicia sesión y obtiene el token Bearer (soportando MFA si está activo)."""
    print(f"[*] Conectando a {API_BASE_URL}/api/v1/auth/login...")
    res = await client.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": "11111111-1", "password": "Cauquenes.2026*"},
        timeout=15.0
    )
    if res.status_code != 200:
        raise RuntimeError(f"Falla de autenticación HTTP {res.status_code}: {res.text}")
    data = res.json()
    if data.get("mfa_required"):
        import pyotp
        totp = pyotp.TOTP("PTAJVCSZ35MSMOB22TUIDDHDS67YEESM")
        v_res = await client.post(
            f"{API_BASE_URL}/api/v1/auth/mfa/verify",
            json={"mfa_token": data["mfa_token"], "totp_code": totp.now()},
            timeout=15.0
        )
        if v_res.status_code != 200:
            raise RuntimeError(f"Falla verificación MFA: {v_res.text}")
        token = v_res.json().get("access_token")
    else:
        token = data.get("access_token")

    if not token:
        raise RuntimeError(f"Login no retornó access_token: {data}")
    print("[+] Autenticación exitosa. Token obtenido.")
    return token

async def enviar_acta(client: httpx.AsyncClient, token: str, payload: dict, semaphore: asyncio.Semaphore, idx: int) -> dict:
    """Envía un acta individual respetando el semáforo de concurrencia."""
    async with semaphore:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        start = datetime.now(timezone.utc)
        res = await client.post(
            f"{API_BASE_URL}/api/v1/infracciones/sync",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        if idx % 20 == 0 or idx == TOTAL_REGISTROS:
            print(f"[*] Progreso: {idx}/{TOTAL_REGISTROS} actas enviadas (HTTP {res.status_code})...", flush=True)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        return {
            "index": idx,
            "status_code": res.status_code,
            "elapsed": elapsed,
            "success": res.status_code == 201,
            "body": res.json() if res.status_code == 201 else res.text
        }

async def main():
    print("=" * 70)
    print("  FISCALIS QA: PRUEBA DE FUNCIONALIDAD Y CARGA MASIVA DE DATOS")
    print(f"  Objetivo: Generar y persistir {TOTAL_REGISTROS} registros a través de la API")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        # 1. Login
        token = await autenticar(client)

        # 2. Preparar los payloads
        print(f"[*] Generando {TOTAL_REGISTROS} actas con datos geográficos de Cauquenes...")
        payloads = []
        base_time = datetime.now(timezone.utc)

        for i in range(TOTAL_REGISTROS):
            acta_id = str(uuid.uuid4())
            marca, modelo, tipo_veh = random.choice(MARCAS_MODELOS)
            color = random.choice(COLORES)
            rut = generar_rut_chileno()
            nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
            ppu = generar_ppu_chilena()
            
            # Coordenadas realistas de Cauquenes, Chile
            lat = round(random.uniform(-35.9750, -35.9550), 6)
            lon = round(random.uniform(-72.3280, -72.3080), 6)
            
            # Fecha dentro de los últimos 20 días
            fecha_acta = base_time - timedelta(days=random.randint(0, 20), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            # 1 a 3 fotos de evidencia con hashes sha256 únicos
            num_fotos = random.randint(1, 3)
            fotos = []
            for f in range(num_fotos):
                h = hashlib.sha256(f"evidencia_{acta_id}_{f}_{uuid.uuid4()}".encode()).hexdigest()
                fotos.append({"hash_sha256": h})

            payload = {
                "id": acta_id,
                "rutInfractor": rut,
                "nombreCompleto": nombre,
                "ppu": ppu,
                "tipoVehiculo": tipo_veh,
                "marcaVehiculo": f"{marca} {modelo}",
                "colorVehiculo": color,
                "tipoInfraccionId": random.choice([1, 2, 3, 4]),
                "coordenadas": f"{lat},{lon}",
                "fotos": fotos,
                "fecha": fecha_acta.isoformat(),
                "descripcion": random.choice(DESCRIPCIONES),
                "firmaRechazo": random.choice([True, False]),
                "status": "EMITIDA"
            }
            payloads.append(payload)

        # 3. Transmisión asíncrona concurrente
        print(f"[*] Transmitiendo {TOTAL_REGISTROS} actas vía POST /api/v1/infracciones/sync (Concurrencia: {CONCURRENCY_LIMIT})...")
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        tasks = [
            enviar_acta(client, token, p, semaphore, idx)
            for idx, p in enumerate(payloads, start=1)
        ]
        
        start_all = datetime.now(timezone.utc)
        results = await asyncio.gather(*tasks)
        total_time = (datetime.now(timezone.utc) - start_all).total_seconds()

        exitosos = [r for r in results if r["success"]]
        fallidos = [r for r in results if not r["success"]]

        print("-" * 70)
        print(f"[+] Total transmitidos: {len(results)}")
        print(f"[+] Exitosos (HTTP 201): {len(exitosos)}")
        print(f"[+] Fallidos: {len(fallidos)}")
        print(f"[+] Tiempo total de inserción: {total_time:.2f} s ({len(results)/total_time:.2f} req/s)")
        if fallidos:
            print(f"[!] Muestra de fallos: {fallidos[:3]}")
            sys.exit(1)

        # 4. Verificación de lectura vía API GET /api/v1/infracciones
        print("\n[*] Validando endpoint de lectura GET /api/v1/infracciones...")
        get_res = await client.get(
            f"{API_BASE_URL}/api/v1/infracciones",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0
        )
        assert get_res.status_code == 200, f"Error al listar: {get_res.status_code}"
        lista = get_res.json()
        print(f"[+] GET /api/v1/infracciones retornó exitosamente {len(lista)} actas sincronizadas.")

    print("\n" + "=" * 70)
    print("  VERIFICACIÓN DIRECTA EN BASE DE DATOS POSTGRESQL + POSTGIS")
    print("=" * 70)

    # 5. Verificación directa en base de datos
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.models.registros import InfraccionVehicular, RegistroBase, EvidenciaFotografica
    from app.models.auditoria import AuditoriaEvento, SyncEvent

    async with AsyncSessionLocal() as session:
        n_infracciones = await session.scalar(select(func.count()).select_from(InfraccionVehicular))
        n_base = await session.scalar(select(func.count()).select_from(RegistroBase))
        n_evidencias = await session.scalar(select(func.count()).select_from(EvidenciaFotografica))
        n_auditoria = await session.scalar(select(func.count()).select_from(AuditoriaEvento))
        n_sync = await session.scalar(select(func.count()).select_from(SyncEvent))

        print(f"[DB] Infracciones Vehiculares totales: {n_infracciones}")
        print(f"[DB] Registros Base (Polimórficos) totales: {n_base}")
        print(f"[DB] Evidencias Fotográficas totales: {n_evidencias}")
        print(f"[DB] Eventos de Auditoría totales: {n_auditoria}")
        print(f"[DB] Eventos de Sincronización totales: {n_sync}")

    print("\n[OK] ¡La base de datos fue alimentada exitosamente y la API respondió al 100%!")

if __name__ == "__main__":
    asyncio.run(main())
