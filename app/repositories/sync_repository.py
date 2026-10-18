import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.registros import InfraccionVehicular, EvidenciaFotografica
from app.schemas.sync import SincronizacionActaRequest

class SyncRepository:
    """
    Repositorio encargado de manejar la persistencia de los datos 
    provenientes de la sincronización Offline-First.
    """
    
    async def procesar_acta_vehicular(self, db: AsyncSession, payload: SincronizacionActaRequest, inspector_id: uuid.UUID) -> InfraccionVehicular:
        from sqlalchemy import select
        from app.models.registros import RegistroBase
        
        # 0. Verificación de idempotencia (Offline-First retry)
        existente = await db.scalar(select(RegistroBase).where(RegistroBase.id == payload.id))
        if existente:
            return existente

        try:
            # 1. Transformación Geoespacial Segura (PostGIS - Sanitización anti-inyección)
            # Extraer lat y lon del string "-35.9664047,-72.3114046"
            partes_coord = payload.coordenadas.split(',')
            lat_raw = partes_coord[0].strip() if len(partes_coord) > 0 else "0"
            lon_raw = partes_coord[1].strip() if len(partes_coord) > 1 else "0"
            try:
                lat_f = float(lat_raw)
                lon_f = float(lon_raw)
                if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
                    lat_f, lon_f = 0.0, 0.0
            except (ValueError, TypeError):
                lat_f, lon_f = 0.0, 0.0
            ubicacion_wkt = f"SRID=4326;POINT({lon_f} {lat_f})"
            
            # 2. Desarmar Payload para InfraccionesVehiculares
            nueva_acta = InfraccionVehicular(
                id=payload.id,
                registro_uuid=payload.id,
                inspector_id=inspector_id,
                modulo="infraccion_vehicular",
                estado=payload.status,
                fecha_emision=payload.fecha,
                ubicacion=ubicacion_wkt,
                ppu=payload.ppu,
                rut_infractor=payload.rutInfractor,
                nombre_completo=payload.nombreCompleto,
                marca=payload.marcaVehiculo or 'No especificado',
                tipo_vehiculo=payload.tipoVehiculo or 'No especificado',
                color=payload.colorVehiculo or 'No especificado',
                tipo_infraccion_id=payload.tipoInfraccionId if payload.tipoInfraccionId is not None else 1,
                observaciones=payload.descripcion or "Sin observaciones"
            )
            
            db.add(nueva_acta)
            await db.flush() # Force insertion to guarantee PK exists
            
            # 3. Procesar Evidencias
            for foto_data in payload.fotos:
                if isinstance(foto_data, dict):
                    hash_val = foto_data.get('hash_sha256', '')
                elif isinstance(foto_data, str):
                    hash_val = foto_data
                else:
                    hash_val = getattr(foto_data, 'hash_sha256', str(foto_data))
                
                nueva_evidencia = EvidenciaFotografica(
                    registro_uuid=nueva_acta.id,
                    hash_sha256=hash_val
                )
                db.add(nueva_evidencia)
                
            # 4. Telemetría y Auditoría (Opcional, pero solicitado por el usuario)
            from app.models.auditoria import AuditoriaEvento, SyncEvent
            
            sync_event = SyncEvent(
                dispositivo_id="Fiscalis Mobile App",
                inspector_id=inspector_id,
                estado="EXITOSO",
                detalles={"acta_id": str(payload.id), "modulo": "infraccion_vehicular"}
            )
            db.add(sync_event)
            
            auditoria = AuditoriaEvento(
                entidad_id=str(payload.id),
                entidad_tipo="InfraccionVehicular",
                accion="CREACION_POR_SYNC",
                usuario_id=inspector_id,
                payload=payload.model_dump(mode='json')
            )
            db.add(auditoria)
                
            # 5. Transaccionalidad ACID
            await db.commit()
            return nueva_acta
            
        except IntegrityError as e:
            await db.rollback()
            # Se relanza para que sea manejada en la capa de servicios o el controlador (ej. duplicados)
            raise e
        except Exception as e:
            await db.rollback()
            raise e
