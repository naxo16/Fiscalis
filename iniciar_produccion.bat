@echo off
title SGF_CORE - Backend Municipal (Simulacion Produccion)
echo ===============================================================================
echo   FISCALIS (SGF_CORE) - INICIANDO BACKEND EN MODO SIMULACION DE PRODUCCION
echo ===============================================================================

:: 1. Verificar si existe el entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encuentra el entorno virtual (venv).
    echo Asegurate de haber ejecutado 'python -m venv venv' y 'pip install -r requirements.txt'
    pause
    exit /b
)

:: 2. Activar entorno virtual
call venv\Scripts\activate

:: 3. Definir variables de entorno para simular producción
set ENVIRONMENT=production
set DEBUG=FALSE

echo [PROD] Servidor ASGI: Uvicorn de alto rendimiento
echo [PROD] Host: 0.0.0.0 (accesible desde localhost, emuladores y red LAN)
echo [PROD] Puerto: 8000
echo [PROD] CORS: Habilitado para Flutter Web (http://localhost:*, http://127.0.0.1:*)
echo [PROD] Healthcheck: http://127.0.0.1:8000/health
echo ===============================================================================

:: 4. Lanzar servidor ASGI en modo producción (sin reloader, multihilo)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --access-log

pause
