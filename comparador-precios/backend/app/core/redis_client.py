import redis.asyncio as redis
from loguru import logger
from app.core.config import settings
from typing import Optional

# Variable global para mantener la instancia del cliente/pool
redis_client: Optional[redis.Redis] = None

async def get_redis_client() -> Optional[redis.Redis]:
    """
    Retorna la instancia del cliente Redis (creada durante el lifespan).
    Esta función es usada principalmente por la dependencia `get_redis` en deps.py.
    """
    return redis_client

async def init_redis_pool():
    """
    Inicializa el pool de conexiones Redis. Llamado en el lifespan de FastAPI.
    """
    global redis_client
    if redis_client is not None:
        logger.info("El pool de Redis ya está inicializado.")
        return

    try:
        # Usar from_url es conveniente ya que maneja la creación del pool
        redis_client = await redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            encoding="utf-8",
            decode_responses=True, # Decodifica respuestas a strings automáticamente
            health_check_interval=30, # Revisa la conexión cada 30s
            socket_connect_timeout=5, # Timeout para conectar
            socket_keepalive=True,
        )
        # Realizar un ping para asegurar la conexión
        await redis_client.ping()
        logger.info(f"Pool de conexiones a Redis establecido exitosamente en {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except redis.exceptions.ConnectionError as e:
        logger.error(f"No se pudo conectar a Redis en {settings.REDIS_HOST}:{settings.REDIS_PORT}. Error: {e}")
        redis_client = None # Asegura que sea None si falla la conexión inicial
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al inicializar el pool de Redis: {e}")
        redis_client = None

async def close_redis_pool():
    """
    Cierra el pool de conexiones Redis. Llamado en el lifespan de FastAPI.
    """
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            # await redis_client.connection_pool.disconnect() # En versiones más nuevas, close() debería ser suficiente
            logger.info("Conexión/Pool de Redis cerrada exitosamente.")
        except Exception as e:
            logger.error(f"Error al cerrar la conexión/pool de Redis: {e}")
        finally:
             redis_client = None # Limpia la referencia global
    else:
        logger.info("No había conexión/pool de Redis activa para cerrar.")
