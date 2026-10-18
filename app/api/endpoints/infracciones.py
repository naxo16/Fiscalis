import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.api.deps import get_db, get_current_inspector
from app.schemas.sync import SincronizacionActaRequest
from app.repositories.sync_repository import SyncRepository
from app.models.registros import InfraccionVehicular

router = APIRouter()
sync_repo = SyncRepository()

@router.post("/sync", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
@router.post("", status_code=status.HTTP_201_CREATED)
async def sincronizar_infracciones(
    payload: SincronizacionActaRequest,
    db: AsyncSession = Depends(get_db),
    inspector_id: uuid.UUID = Depends(get_current_inspector)
):
    """
    Endpoint crítico Offline-First.
    Recibe el payload masivo desde SQLite y lo sincroniza en PostgreSQL.
    """
    try:
        acta = await sync_repo.procesar_acta_vehicular(
            db=db, 
            payload=payload, 
            inspector_id=inspector_id
        )
        return {"message": "Sincronización exitosa", "id": acta.id}
        
    except IntegrityError as e:
        import logging
        logging.error(f"IntegrityError: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflicto de integridad. El registro o la evidencia ya existen en el servidor. {str(e)}"
        )
    except Exception as e:
        import logging
        logging.error(f"Server error during sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno en servidor. Gatillar Exponential Backoff: {str(e)}"
        )

@router.get("", status_code=status.HTTP_200_OK)
async def listar_infracciones(
    db: AsyncSession = Depends(get_db),
    inspector_id: uuid.UUID = Depends(get_current_inspector)
):
    """
    Endpoint para listar los resultados de las infracciones sincronizadas.
    """
    # En un escenario real esto se manejaría en un InfraccionRepository
    result = await db.scalars(select(InfraccionVehicular))
    infracciones = result.all()
    
    return [
        {
            "id": i.id,
            "estado": i.estado,
            "ppu": i.ppu,
            "fecha_emision": i.fecha_emision
        } 
        for i in infracciones
    ]