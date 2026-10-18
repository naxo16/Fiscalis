# SGF_CORE Backend - Sistema de Gestión Fiscalizadora Municipal

Motor transaccional y validador de alto rendimiento para fiscalización municipal y registro de infracciones vehiculares en terreno, construido con **FastAPI** y **PostgreSQL + PostGIS**. Diseñado bajo principios de **Clean Architecture** para servir como nodo central en una solución distribuida **Offline-First**.

---

## 🚀 Tecnologías Clave

- **Framework Web:** FastAPI (Asíncrono, Python 3.12+)
- **Base de Datos Geoespacial:** PostgreSQL 16 + PostGIS (`geometry(Point, 4326)`)
- **ORM Asíncrono:** SQLAlchemy 2.0 + Asyncpg
- **Migraciones:** Alembic
- **Seguridad y Criptografía:** JWT Stateless (HS256), Multi-Factor Authentication TOTP (RFC 6238), Rotación de llaves Fernet (AES-256)
- **CORS Multi-Origen:** Configuración permisiva y headers CORP para interoperabilidad con Flutter Web CanvasKit
- **Validación de Esquemas:** Pydantic V2
- **QA & Testing:** Pytest 9 + Pytest-Asyncio + HTTPX

---

## 🏗️ Estructura del Repositorio

```
sgf_backend/
├── app/
│   ├── api/            # Capa de red (Routers, Middleware CORS, Inyección de dependencias)
│   │   ├── endpoints/  # Controladores (auth, infracciones, evidencias, salud)
│   │   └── deps.py     # Dependencias de seguridad e inyección de AsyncSession
│   ├── core/           # Configuración (settings, database engine, hashing de contraseñas)
│   ├── models/         # Modelos SQLAlchemy relacionales y geoespaciales
│   ├── repositories/   # Capa de acceso a datos (Patrón Repositorio)
│   ├── schemas/        # DTOs y contratos Pydantic para validación de entrada/salida
│   ├── services/       # Servicios de negocio (almacenamiento de archivos, Magic Bytes)
│   └── tests/          # Suite de pruebas automatizadas (17 tests asíncronos)
├── scripts/            # Scripts de inicialización, seeds y comprobación de integridad
├── alembic/            # Migraciones versionadas de esquema de base de datos
├── Dockerfile          # Empaquetado de producción multi-etapa
├── docker-compose.yml  # Orquestador con PostgreSQL 16 PostGIS y backend FastAPI
└── requirements.txt    # Dependencias congeladas
```

---

## 🛠️ Instalación y Puesta en Marcha

### Opción 1: Despliegue con Docker Compose (Recomendado para Producción)

```bash
# 1. Clonar variables de entorno
cp .env.example .env

# 2. Levantar el stack completo (Base de datos PostGIS + API Backend)
docker compose up -d --build
```

### Opción 2: Instalación Local con Entorno Virtual

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Aplicar migraciones
alembic upgrade head

# 4. Iniciar servidor de desarrollo
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🧪 Pruebas Automatizadas (QA Suite)

Para ejecutar la suite de 17 pruebas asíncronas:
```bash
pytest app/tests -v
```

Cobertura verificada:
1. `test_health.py`: Verificación de salud y versión del sistema.
2. `test_auth.py`: Autenticación por contraseña, MFA TOTP, validación de sesiones y rechazo de tokens inválidos.
3. `test_cors_flutter_web.py`: Preflight OPTIONS de origen cruzado para puertos dinámicos de Flutter Web.
4. `test_infracciones.py`: Rechazo de payloads malformados (422) y manejo de caídas de BD (500 Exponential Backoff).
5. `test_sync_e2e.py`: Idempotencia de transacciones, persistencia geométrica PostGIS y serialización de actas.