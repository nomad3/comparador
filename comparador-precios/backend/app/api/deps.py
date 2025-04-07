from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import redis.asyncio as redis
from loguru import logger

from app.db.session import SessionLocal
from app.core.redis_client import get_redis_client as get_redis_pool_client # Renombrado para claridad

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos SQLAlchemy.

    Maneja la creación y cierre de la sesión automáticamente.
    Lanza HTTPException si la fábrica de sesiones no está disponible.
    """
    if SessionLocal is None:
        logger.error("La fábrica de sesiones (SessionLocal) no está inicializada.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La conexión a la base de datos no está disponible.",
        )

    db: Optional[Session] = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        # Podrías querer loggear el error específico aquí
        logger.error(f"Error durante la sesión de base de datos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al procesar la solicitud de base de datos.",
        )
    finally:
        if db is not None:
            db.close()
            # logger.trace("Sesión de base de datos cerrada.") # Log muy verboso

async def get_redis_client() -> redis.Redis:
    """
    Dependencia de FastAPI para obtener el cliente Redis asíncrono.

    Obtiene el cliente inicializado desde el pool gestionado en el lifespan.
    Lanza HTTPException si el cliente no está disponible.
    """
    client = await get_redis_pool_client() # Usa la función del core.redis_client
    if client is None:
        logger.error("El cliente Redis no está disponible (no inicializado o conexión fallida).")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de caché (Redis) no está disponible.",
        )
    # logger.trace("Cliente Redis obtenido del pool.") # Log muy verboso
    return client

# Podrías añadir otras dependencias aquí, como obtener el usuario actual si tuvieras autenticación.
# def get_current_user(...) -> models.User: ...
