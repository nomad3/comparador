import httpx
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field, ValidationError
from loguru import logger
import decimal

from app.core.config import settings

# --- Input/Output Models for Scrapers ---

class ScraperInput(BaseModel):
    """Datos de entrada para un scraper."""
    query: str = Field(..., description="Término de búsqueda")
    source_id: int = Field(..., description="ID de la fuente (tabla sources)")
    source_name: str = Field(..., description="Nombre de la fuente")
    base_url: str = Field(..., description="URL base de la fuente para construir URLs de búsqueda")

class ScrapedData(BaseModel):
    """Datos estandarizados devueltos por un scraper."""
    source_product_name: str
    price: decimal.Decimal
    currency: str = 'CLP' # Default currency
    product_url: HttpUrl
    # Opcional: Añadir más campos si se pueden extraer consistentemente
    # image_url: Optional[HttpUrl] = None
    attributes: Optional[Dict[str, Any]] = None # Para datos extra

# --- Base Scraper Class ---

class BaseScraper(ABC):
    """
    Clase base abstracta para todos los scrapers de sitios web.
    Define la interfaz común y proporciona utilidades básicas.
    """
    def __init__(self, scraper_input: ScraperInput):
        self.input = scraper_input
        self.client = httpx.AsyncClient(
            headers=settings.SCRAPER_DEFAULT_HEADERS,
            timeout=settings.SCRAPER_TIMEOUT_SECONDS,
            follow_redirects=True, # Seguir redirecciones automáticamente
            http2=True # Intentar usar HTTP/2 si está disponible
        )
        self.logger = logger.bind(scraper=self.__class__.__name__, query=self.input.query, source=self.input.source_name)

    @abstractmethod
    async def _build_search_url(self) -> str:
        """
        Construye la URL de búsqueda específica para el sitio web.
        Debe ser implementado por cada subclase.
        """
        pass

    @abstractmethod
    async def _parse_results(self, content: str) -> List[ScrapedData]:
        """
        Parsea el contenido HTML de la página de resultados.
        Debe ser implementado por cada subclase.
        Retorna una lista de objetos ScrapedData.
        """
        pass

    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Realiza la petición HTTP para obtener el contenido de la página.
        Maneja errores básicos de conexión.
        """
        try:
            self.logger.info(f"Realizando petición GET a: {url}")
            response = await self.client.get(url)
            response.raise_for_status() # Lanza excepción para códigos 4xx/5xx
            self.logger.success(f"Petición a {url} exitosa (Status: {response.status_code})")
            return response.text
        except httpx.TimeoutException:
            self.logger.error(f"Timeout al intentar acceder a {url}")
        except httpx.RequestError as e:
            self.logger.error(f"Error de red al acceder a {url}: {e.__class__.__name__} - {e}")
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Error HTTP {e.response.status_code} al acceder a {url}")
        except Exception as e:
            self.logger.error(f"Error inesperado al acceder a {url}: {e.__class__.__name__} - {e}")
        return None

    async def scrape(self) -> List[ScrapedData]:
        """
        Orquesta el proceso de scraping: construye URL, obtiene página, parsea resultados.
        """
        search_url = await self._build_search_url()
        if not search_url:
            self.logger.error("No se pudo construir la URL de búsqueda.")
            return []

        page_content = await self.fetch_page(search_url)
        if not page_content:
            self.logger.error("No se pudo obtener el contenido de la página de búsqueda.")
            return []

        try:
            self.logger.info("Parseando resultados...")
            results = await self._parse_results(page_content)
            self.logger.success(f"Se encontraron {len(results)} resultados potenciales.")
            # Validar los resultados con Pydantic
            validated_results = []
            for i, item in enumerate(results):
                try:
                    # Intentar validar/crear el objeto ScrapedData
                    validated_item = ScrapedData(**item.model_dump()) # Usar model_dump en Pydantic v2
                    validated_results.append(validated_item)
                except ValidationError as e:
                    self.logger.warning(f"Error de validación en item {i+1}: {e}. Item omitido: {item}")
                except Exception as e:
                     self.logger.warning(f"Error inesperado al procesar item {i+1}: {e}. Item omitido: {item}")

            self.logger.success(f"Se validaron {len(validated_results)} resultados.")
            return validated_results
        except Exception as e:
            self.logger.exception("Error crítico durante el parseo de resultados.")
            # self.logger.error(f"Error durante el parseo: {e.__class__.__name__} - {e}")
            return []
        finally:
            # Asegurarse de cerrar el cliente HTTP
            await self.client.aclose()
            self.logger.info("Cliente HTTP cerrado.")

    # --- Helper Methods ---
    def _clean_text(self, text: Optional[str]) -> str:
        """Limpia espacios en blanco y caracteres especiales de un texto."""
        if text is None:
            return ""
        return " ".join(text.strip().split())

    def _extract_price(self, price_text: Optional[str]) -> Optional[decimal.Decimal]:
        """Intenta extraer y limpiar un precio de un string."""
        if not price_text:
            return None
        try:
            # Eliminar símbolos de moneda, puntos de miles, espacios
            cleaned_price = price_text.replace("$", "").replace(".", "").replace(" ", "").strip()
            # Reemplazar coma decimal por punto si es necesario (depende de la localización)
            cleaned_price = cleaned_price.replace(",", ".")
            # Intentar convertir a Decimal
            return decimal.Decimal(cleaned_price)
        except (ValueError, decimal.InvalidOperation) as e:
            self.logger.warning(f"No se pudo convertir el texto '{price_text}' a Decimal: {e}")
            return None
