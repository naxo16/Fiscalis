# Dockerfile para SGF_CORE Backend (Fiscalis)
# Optimizado para producción institucional con Python 3.12 y soporte PostGIS

FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias de compilación para paquetes nativos (asyncpg, cryptography, geoalchemy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Etapa Final de Producción ---
FROM python:3.12-slim AS runner

WORKDIR /app

# Instalar librerías de runtime necesarias (libpq para PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias de Python desde la etapa builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Crear usuario sin privilegios para seguridad (OWASP ASVS)
RUN groupadd -r fiscalis && useradd -r -g fiscalis fiscalis

# Copiar código fuente y directorios necesarios
COPY . /app
RUN mkdir -p /app/storage/evidencias && chown -R fiscalis:fiscalis /app

USER fiscalis

EXPOSE 8000

# Health check nativo de contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
