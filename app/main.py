# -*- coding: utf-8 -*-
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.infracciones import router as infracciones_router

# Configuración de Logging para Producción
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("fiscalis.core")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de arranque (Startup)
    logger.info("==================================================")
    logger.info(f"Iniciando {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")
    logger.info("Verificando conectividad con el cluster PostgreSQL...")
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Conexión con PostgreSQL/PostGIS verificada exitosamente.")
    except Exception as e:
        logger.warning(f"Advertencia al conectar con la base de datos en inicio: {e}")
    logger.info("==================================================")
    
    yield
    
    # Lógica de apagado (Shutdown)
    logger.info("Cerrando pool de conexiones de base de datos...")
    await engine.dispose()
    logger.info("Servidor Fiscalis apagado correctamente.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    description="Backend Institucional para el Sistema de Gestión Fiscalizadora (SGF) - Simulación Producción"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Error de validación 422 en {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.middleware("http")
async def add_security_and_corp_headers(request: Request, call_next):
    response = await call_next(request)
    # Soporte para Cross-Origin Resource Policy (CORP) requerido por Flutter Web
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    return response

# Configuración avanzada de CORS para Flutter Web y producción
# Soporta cualquier puerto de localhost/127.0.0.1 (ej. Flutter Web en :1859, :3000, etc.)
# y orígenes explícitos configurados en el entorno institucional
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else [],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$" if "*" in origins else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Authorization", "X-Total-Count", "Content-Disposition"]
)

# Registro de Routers Institucionales
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Autenticación y MFA"]
)

app.include_router(
    infracciones_router,
    prefix=f"{settings.API_V1_STR}/infracciones",
    tags=["Sincronización Offline-First e Infracciones"]
)

@app.get("/", tags=["Infraestructura"])
async def root():
    """Ruta raíz de presentación de la API institucional."""
    return {
        "sistema": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "entorno": settings.ENVIRONMENT,
        "estado": "operativo",
        "docs": f"{settings.API_V1_STR}/openapi.json"
    }

@app.get("/health", tags=["Infraestructura"])
async def health_check():
    """Health check de grado de producción que valida el pool de base de datos."""
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Falla de salud en base de datos: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": f"unreachable: {str(e)}",
                "system": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT
            }
        )
        
    return {
        "status": "ok",
        "database": db_status,
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }