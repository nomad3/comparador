from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
import redis.asyncio as redis
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from loguru import logger

from app import models, schemas, crud
from app.api import deps
from app.services.search_service import SearchService
from app.core.config import settings

router = APIRouter()

# --- Helper Function ---
def are_results_stale(results: List[schemas.SearchResultItem], max_age_hours: int = 1) -> bool:
    """
    Verifica si alguno de los resultados es más antiguo que max_age_hours.
    Retorna True si están obsoletos o la lista está vacía, False si son recientes.
    """
    if not results:
        return True # Si no hay resultados, considerar obsoleto para forzar scraping

    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=max_age_hours)

    for item in results:
        # Asegurarse que scraped_at sea timezone-aware (UTC)
        scraped_at_aware = item.scraped_at.replace(tzinfo=timezone.utc) if item.scraped_at.tzinfo is None else item.scraped_at
        if scraped_at_aware < threshold:
            logger.debug(f"Resultado obsoleto encontrado (scraped: {scraped_at_aware}, threshold: {threshold})")
            return True # Encontró uno obsoleto, no necesita seguir revisando
    return False # Ningún resultado es más antiguo que el umbral

# --- Search Endpoint ---

@router.get("/", response_model=schemas.SearchResponse)
async def search_products(
    *,
    db: Session = Depends(deps.get_db),
    redis_client: redis.Redis = Depends(deps.get_redis_client),
    background_tasks: BackgroundTasks,
    query: str = Query(..., min_length=3, max_length=100, description="Término de búsqueda"),
    force_refresh: bool = Query(False, description="Forzar scraping ignorando caché y datos recientes de DB")
):
    """
    Endpoint principal de búsqueda.

    1.  Intenta obtener resultados de la caché (si `force_refresh` es False).
    2.  Si no hay caché o `force_refresh` es True, obtiene resultados de la DB.
    3.  Decide si iniciar un scraping en segundo plano:
        *   Si `force_refresh` es True.
        *   Si los resultados de la DB están vacíos.
        *   Si los resultados de la DB son más antiguos que un umbral (ej: 1 hora).
        *   Si no hay un job de scraping PENDIENTE o EN CURSO para esta query.
    4.  Retorna los resultados (de caché o DB) y un mensaje si el scraping se inició.
    """
    search_service = SearchService(db=db, redis_client=redis_client)
    job_id: Optional[int] = None
    message: Optional[str] = None

    # 1 & 2: Obtener resultados (cache o DB)
    results, from_cache, _ = await search_service.get_search_results(query=query, force_refresh=force_refresh)
    logger.info(f"Búsqueda para '{query}'. Obtenidos {len(results)} resultados. Desde caché: {from_cache}. Force refresh: {force_refresh}")

    # 3: Decidir si iniciar scraping
    should_scrape = False
    if force_refresh:
        should_scrape = True
        message = "Scraping forzado iniciado en segundo plano."
        logger.info(f"Scraping forzado para '{query}'.")
    else:
        # Verificar si los resultados (de DB, ya que si vino de caché no forzamos) son obsoletos
        if not from_cache and are_results_stale(results, max_age_hours=1):
             should_scrape = True
             message = "Datos existentes obsoletos o no encontrados. Iniciando scraping en segundo plano."
             logger.info(f"Resultados obsoletos o no encontrados para '{query}'. Se iniciará scraping.")
        elif not results and not from_cache:
             # Caso especial: No vino de caché y la DB no tiene nada
             should_scrape = True
             message = "No se encontraron datos. Iniciando scraping en segundo plano."
             logger.info(f"No hay resultados en DB para '{query}'. Se iniciará scraping.")


    if should_scrape:
        # Verificar si ya hay un job PENDIENTE o RUNNING para esta query
        existing_job = crud.scrape_job.get_pending_for_query(db, query_term=query)
        if existing_job:
            logger.info(f"Ya existe un job de scraping {existing_job.status} (ID: {existing_job.job_id}) para '{query}'. No se iniciará uno nuevo.")
            message = f"Ya hay un scraping en estado '{existing_job.status}' para esta búsqueda."
            job_id = existing_job.job_id
        else:
            # Crear un nuevo job de scraping
            try:
                new_job_schema = schemas.ScrapeJobCreate(query_term=query, status='PENDING')
                new_job = crud.scrape_job.create(db=db, obj_in=new_job_schema)
                job_id = new_job.job_id
                logger.info(f"Creado nuevo ScrapeJob (ID: {job_id}) para '{query}'. Añadiendo a background tasks.")
                # Añadir la tarea de scraping al fondo
                # Pasamos una nueva instancia de SearchService porque la sesión de DB
                # de la request principal se cierra al terminar la request.
                # BackgroundTasks necesita su propia sesión.
                background_tasks.add_task(
                    run_background_scraping, query, job_id
                )
                message = message or "Iniciando scraping en segundo plano." # Usar mensaje por defecto si no se estableció antes
            except Exception as e:
                 logger.exception(f"Error al crear ScrapeJob o añadir background task para '{query}': {e}")
                 # No lanzar excepción al cliente, pero loggear el error
                 message = "Error al iniciar el proceso de scraping en segundo plano."


    # 4: Retornar respuesta
    return schemas.SearchResponse(
        query=query,
        results=results,
        from_cache=from_cache and not force_refresh, # Solo es de caché si no se forzó refresh
        message=message,
        job_id=job_id
    )


# --- Función para Tarea en Segundo Plano ---

def run_background_scraping(query: str, job_id: int):
    """
    Función ejecutada por BackgroundTasks.
    Necesita crear su propia sesión de DB y cliente Redis.
    """
    logger.info(f"[Background] Iniciando scraping para Job ID: {job_id}, Query: '{query}'")
    db: Optional[Session] = None
    redis_client_bg: Optional[redis.Redis] = None # Necesitamos un cliente sync o manejar async aquí

    # --- Manejo Asíncrono dentro de Tarea Síncrona ---
    # BackgroundTasks de FastAPI ejecuta funciones síncronas.
    # Para llamar a nuestro SearchService asíncrono, necesitamos un event loop.
    async def async_scraping_wrapper():
        nonlocal db, redis_client_bg # Modificar variables externas
        try:
            # Crear sesión de DB para esta tarea
            db = next(deps.get_db()) # Obtener sesión del generador

            # Crear cliente Redis para esta tarea (o reutilizar si es seguro)
            # NOTA: El cliente Redis del lifespan podría no ser seguro usarlo directamente
            #       en un thread/task diferente. Crear uno nuevo es más seguro.
            redis_client_bg = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8", decode_responses=True
            )
            await redis_client_bg.ping() # Verificar conexión

            # Crear instancia del servicio con la nueva sesión/cliente
            service = SearchService(db=db, redis_client=redis_client_bg)

            # Ejecutar el scraping
            await service.perform_scraping(query=query, job_id=job_id)

            logger.success(f"[Background] Scraping finalizado para Job ID: {job_id}, Query: '{query}'")

        except Exception as e:
            logger.exception(f"[Background] Error crítico durante scraping para Job ID {job_id}: {e}")
            # Intentar marcar el job como FAILED si aún tenemos sesión de DB
            if db and job_id:
                try:
                    crud.scrape_job.mark_as_failed(db, job_id=job_id, error_message=f"Background task error: {e.__class__.__name__}")
                except Exception as db_err:
                     logger.error(f"[Background] Error al marcar job {job_id} como FAILED en DB: {db_err}")
        finally:
            # Asegurarse de cerrar la sesión de DB y cliente Redis de la tarea
            if db:
                db.close()
            if redis_client_bg:
                 await redis_client_bg.close()
            logger.info(f"[Background] Recursos limpiados para Job ID: {job_id}")

    # Ejecutar la función asíncrona dentro de la tarea síncrona
    try:
        asyncio.run(async_scraping_wrapper())
    except RuntimeError as e:
         # Esto puede pasar si ya hay un loop corriendo (ej: en algunos entornos de prueba)
         # Intentar obtener el loop existente
         loop = asyncio.get_event_loop()
         if loop.is_running():
              logger.warning(f"[Background] Event loop ya está corriendo. Usando loop existente para Job ID: {job_id}")
              # Crear una tarea en el loop existente
              loop.create_task(async_scraping_wrapper())
              # Nota: Esto no esperará a que la tarea termine aquí.
              # Considerar usar asyncio.run_coroutine_threadsafe si se ejecuta desde otro thread.
         else:
              logger.error(f"[Background] Error de Runtime al ejecutar async wrapper para Job ID {job_id}: {e}")
