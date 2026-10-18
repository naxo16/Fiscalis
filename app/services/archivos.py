# app/services/archivos.py
import os
import uuid
import hashlib
import aiofiles
import logging

# Intentamos importar magic, si falla, manejamos el error elegantemente
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logging.warning("Librería 'python-magic' no encontrada o mal configurada. Usando fallback de extensión.")

from fastapi import UploadFile

STORAGE_DIR = "storage/evidencias"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Extensiones y Mimes permitidos
ALLOWED_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png"
}

class ArchivosService:
    @staticmethod
    async def procesar_y_guardar_evidencia(acta_id: str, file: UploadFile) -> dict:
        
        # 1. Determinación del MimeType (Estrategia híbrida)
        mime_detectado = None
        
        if MAGIC_AVAILABLE:
            try:
                header = await file.read(2048)
                await file.seek(0)
                mime_detectado = magic.from_buffer(header, mime=True)
            except Exception as e:
                logging.error(f"Error en libmagic: {e}")
        
        # Fallback si magic falló o no está disponible
        if mime_detectado not in ALLOWED_TYPES.values():
            ext = os.path.splitext(file.filename or "")[1].lower()
            mime_detectado = ALLOWED_TYPES.get(ext)
            
        if not mime_detectado:
            raise ValueError(f"Tipo de archivo no soportado o no detectado.")

        # 2. Generar el path y hashear
        sha256_hash = hashlib.sha256()
        file_ext = "jpg" if "jpeg" in mime_detectado else "png"
        file_name = f"{acta_id}_{uuid.uuid4().hex[:8]}.{file_ext}" # UUID corto para evitar colisiones
        file_path = os.path.join(STORAGE_DIR, file_name)

        # 3. Guardado seguro
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(1024 * 1024):
                sha256_hash.update(content)
                await out_file.write(content)

        file_stats = os.stat(file_path)
        return {
            "ruta_archivo": file_path,
            "mime_type": mime_detectado,
            "peso_bytes": file_stats.st_size,
            "hash_sha256": sha256_hash.hexdigest()
        }