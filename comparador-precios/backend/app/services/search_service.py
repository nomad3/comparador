import asyncio
from datetime import datetime, timedelta, timezone
import json
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
import redis.asyncio as redis
from loguru import logger

from app.core.config import settings
from app import crud, models, schemas
from app.scrapers import SCRAPER_MAPPING, BaseScraper, ScraperInput, ScrapedData

class SearchService:
    """
    Servicio para manejar la lógica de búsqueda, caché y scraping.
    """

    def __init__(self, db: Session, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.logger = logger.bind(service="SearchService")

    async def _get_cache_key(self, query: str) -> str:
        """Genera la clave de caché para una consulta."""
        return f"search:{query.lower().strip()}"

    async def _get_results_from_cache(self, query: str) -> Optional[List[schemas.SearchResultItem]]:
        """Intenta obtener resultados desde la caché Redis."""
        cache_key = await self._get_cache_key(query)
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            try:
                self.logger.info(f"Cache HIT para la consulta: '{query}' (Key: {cache_key})")
                # Decodificar JSON y validar con Pydantic
                results_dict = json.loads(cached_data)
                # Convertir de nuevo a SearchResultItem (Pydantic v2 maneja bien dicts)
                return [schemas.SearchResultItem(**item) for item in results_dict]
            except json.JSONDecodeError:
                self.logger.error(f"Error al decodificar JSON de caché para la clave: {cache_key}")
            except Exception as e:
                 self.logger.exception(f"Error al procesar datos de caché para la clave {cache_key}: {e}")
        self.logger.info(f"Cache MISS para la consulta: '{query}' (Key: {cache_key})")
        return None

    async def _set_results_to_cache(self, query: str, results: List[schemas.SearchResultItem]):
        """Guarda los resultados en la caché Redis."""
        cache_key = await self._get_cache_key(query)
        try:
            # Convertir resultados Pydantic a lista de dicts para JSON
            results_dict = [item.model_dump(mode='json') for item in results] # Pydantic v2
            await self.redis.set(
                cache_key,
                json.dumps(results_dict),
                ex=settings.CACHE_EXPIRATION_SECONDS
            )
            self.logger.info(f"Resultados guardados en caché para la consulta: '{query}' (Key: {cache_key})")
        except Exception as e:
            self.logger.exception(f"Error al guardar resultados en caché para la clave {cache_key}: {e}")

    def _get_active_sources(self) -> List[models.SourceDB]:
        """Obtiene todas las fuentes activas desde la base de datos."""
        # En el futuro, podríamos tener un flag 'is_active' en SourceDB
        return crud.source.get_multi(self.db, limit=1000) # Asumir que no hay miles de fuentes

    async def _run_scraper_task(self, source: models.SourceDB, query: str) -> List[models.PriceCreate]:
        """Ejecuta el scraper para una fuente específica y retorna datos para crear precios."""
        scraper_cls = SCRAPER_MAPPING.get(source.name)
        if not scraper_cls:
            self.logger.warning(f"No se encontró scraper para la fuente: {source.name}")
            return []

        self.logger.info(f"Iniciando scraping para '{query}' en {source.name}...")
        scraper_input = ScraperInput(
            query=query,
            source_id=source.source_id,
            source_name=source.name,
            base_url=source.base_url
        )
        scraper: BaseScraper = scraper_cls(scraper_input)
        scraped_data: List[ScrapedData] = await scraper.scrape()

        prices_to_create: List[models.PriceCreate] = []
        if scraped_data:
            self.logger.success(f"Scraping completado para {source.name}. {len(scraped_data)} items encontrados.")
            for item in scraped_data:
                # Convertir ScrapedData a PriceCreate
                prices_to_create.append(
                    schemas.PriceCreate(
                        product_query_term=query,
                        source_id=source.source_id,
                        source_product_name=item.source_product_name,
                        price=item.price,
                        currency=item.currency,
                        product_url=item.product_url,
                        attributes=item.attributes
                    )
                )
        else:
             self.logger.warning(f"Scraping para {source.name} no devolvió resultados.")

        # Actualizar timestamp de último scrapeo para la fuente (opcional)
        # crud.source.update(self.db, db_obj=source, obj_in=schemas.SourceUpdate(last_scraped_at=datetime.now(timezone.utc)))

        return prices_to_create

    async def perform_scraping(self, query: str, job_id: Optional[int] = None):
        """
        Realiza el scraping en todas las fuentes activas de forma concurrente.
        Guarda los resultados en la base de datos.
        Actualiza el estado del ScrapeJob si se proporciona un job_id.
        """
        if job_id:
            crud.scrape_job.mark_as_running(self.db, job_id=job_id)

        active_sources = self._get_active_sources()
        if not active_sources:
            self.logger.warning("No hay fuentes activas configuradas para scraping.")
            if job_id: crud.scrape_job.mark_as_failed(self.db, job_id=job_id, error_message="No active sources")
            return

        self.logger.info(f"Iniciando scraping concurrente para '{query}' en {len(active_sources)} fuentes...")

        # Ejecutar tareas de scraping en paralelo
        tasks = [self._run_scraper_task(source, query) for source in active_sources]
        results_list: List[List[models.PriceCreate]] = await asyncio.gather(*tasks, return_exceptions=True)

        all_prices_to_create: List[models.PriceCreate] = []
        errors_occurred = False
        error_messages = []

        for i, result in enumerate(results_list):
            source_name = active_sources[i].name
            if isinstance(result, Exception):
                errors_occurred = True
                error_msg = f"Error en scraper {source_name}: {result.__class__.__name__}"
                self.logger.exception(f"Error ejecutando scraper para {source_name}: {result}")
                error_messages.append(error_msg)
            elif isinstance(result, list):
                all_prices_to_create.extend(result)
            else:
                 # Caso inesperado
                 errors_occurred = True
                 error_msg = f"Resultado inesperado del scraper {source_name}: {type(result)}"
                 self.logger.error(error_msg)
                 error_messages.append(error_msg)


        self.logger.info(f"Scraping concurrente finalizado. {len(all_prices_to_create)} precios potenciales encontrados en total.")

        # Guardar resultados en la base de datos usando create_multi para eficiencia
        if all_prices_to_create:
            try:
                crud.price.create_multi(self.db, objs_in=all_prices_to_create)
                self.logger.success(f"Guardados/Actualizados {len(all_prices_to_create)} precios en la base de datos.")
            except Exception as e:
                self.logger.exception("Error al guardar precios en la base de datos.")
                errors_occurred = True
                error_messages.append(f"DB Error: {e.__class__.__name__}")

        # Actualizar estado del Job
        if job_id:
            if errors_occurred:
                crud.scrape_job.mark_as_failed(self.db, job_id=job_id, error_message="; ".join(error_messages))
            else:
                crud.scrape_job.mark_as_completed(self.db, job_id=job_id)

        # Invalidar/Actualizar caché después del scraping (opcional, podría hacerse en el endpoint)
        # await self._set_results_to_cache(query, await self.get_results_from_db(query))


    def _format_db_results(self, db_prices: List[models.PriceDB]) -> List[schemas.SearchResultItem]:
        """Convierte resultados de la DB al formato de respuesta API."""
        results = []
        for price_db in db_prices:
            if price_db.source: # Asegurarse que la fuente fue cargada (joinedload)
                results.append(
                    schemas.SearchResultItem(
                        source_name=price_db.source.name,
                        source_product_name=price_db.source_product_name,
                        price=price_db.price,
                        currency=price_db.currency,
                        product_url=price_db.product_url, # Ya es string en DB
                        scraped_at=price_db.scraped_at
                    )
                )
            else:
                 self.logger.warning(f"Precio con ID {price_db.price_id} no tiene información de fuente cargada.")
        return results

    async def get_search_results(self, query: str, force_refresh: bool = False) -> Tuple[List[schemas.SearchResultItem], bool, Optional[int]]:
        """
        Obtiene los resultados de búsqueda.
        1. Intenta desde caché (a menos que force_refresh=True).
        2. Si no está en caché o se fuerza refresh, obtiene desde DB.
        3. (La lógica de iniciar scraping se manejará en el endpoint con BackgroundTasks).

        Retorna: (lista de resultados, si vino de caché, ID del job si se creó uno)
        NOTA: Esta versión simplificada NO inicia scraping directamente.
              El endpoint decidirá si iniciar un job basado en si hay datos frescos en DB.
        """
        if not force_refresh:
            cached_results = await self._get_results_from_cache(query)
            if cached_results is not None: # Puede ser lista vacía si la query no tiene resultados
                return cached_results, True, None # Resultados de caché, True, sin Job ID

        # Si no hay caché o se fuerza refresh, obtener de la DB
        # Considerar qué tan "frescos" deben ser los datos de la DB
        # Por ahora, simplemente obtenemos lo último que haya
        self.logger.info(f"Obteniendo resultados de la DB para: '{query}'")
        db_prices = crud.price.get_multi_by_query(
            self.db,
            query_term=query,
            limit=200, # Limitar resultados de DB
            include_source=True # Cargar info de la fuente
        )

        formatted_results = self._format_db_results(db_prices)

        # Guardar en caché los resultados obtenidos de la DB
        if formatted_results:
             await self._set_results_to_cache(query, formatted_results)

        return formatted_results, False, None # Resultados de DB, False, sin Job ID
