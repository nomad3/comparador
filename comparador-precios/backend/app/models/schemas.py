from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
import decimal

# --- Model Configuration ---
# Common configuration for Pydantic models using SQLAlchemy ORM objects
model_config = ConfigDict(from_attributes=True)

# --- Modelos para Fuentes ---
class SourceBase(BaseModel):
    name: str = Field(..., max_length=100, description="Nombre único de la fuente de datos (ej: MercadoLibre Chile)")
    base_url: HttpUrl = Field(..., description="URL base del sitio web de la fuente")

class SourceCreate(SourceBase):
    # No fields needed beyond Base for creation in this simple case
    pass

class SourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    base_url: Optional[HttpUrl] = None
    last_scraped_at: Optional[datetime] = None

class Source(SourceBase):
    model_config = model_config # Enable ORM mode / from_attributes
    source_id: int = Field(..., description="ID único de la fuente")
    last_scraped_at: Optional[datetime] = Field(None, description="Timestamp de la última vez que se scrapeó esta fuente")
    created_at: datetime = Field(..., description="Timestamp de creación del registro")

# --- Modelos para Precios ---
class PriceBase(BaseModel):
    source_product_name: str = Field(..., max_length=500, description="Nombre del producto tal como aparece en la fuente")
    price: decimal.Decimal = Field(..., max_digits=12, decimal_places=2, description="Precio del producto")
    currency: str = Field(default='CLP', max_length=10, description="Moneda del precio (ej: CLP, USD)")
    product_url: HttpUrl = Field(..., description="URL directa al producto en la fuente")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Datos extra no estructurados (JSON)")

class PriceCreate(PriceBase):
    product_query_term: str = Field(..., max_length=255, description="Término de búsqueda que originó este precio")
    source_id: int = Field(..., description="ID de la fuente a la que pertenece este precio")

class PriceUpdate(BaseModel):
    # Qué campos se pueden actualizar? Quizás solo el precio y atributos?
    price: Optional[decimal.Decimal] = Field(None, max_digits=12, decimal_places=2)
    attributes: Optional[Dict[str, Any]] = None
    # No deberíamos actualizar source_id, product_url, query_term, etc.

class Price(PriceBase):
    model_config = model_config
    price_id: int = Field(..., description="ID único del registro de precio")
    source_id: int = Field(..., description="ID de la fuente")
    product_query_term: str = Field(..., max_length=255)
    scraped_at: datetime = Field(..., description="Timestamp de cuándo se obtuvo este precio")
    # Opcional: Incluir la información completa de la fuente si se necesita
    source: Optional[Source] = Field(None, description="Información de la fuente asociada")


# --- Modelos para Búsqueda ---
class SearchQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=100, description="Término de búsqueda del usuario")
    force_refresh: bool = Field(default=False, description="Forzar scraping ignorando caché")

class SearchResultItem(BaseModel):
    # Similar a Price, pero seleccionando campos para la respuesta API
    source_name: str = Field(..., description="Nombre de la tienda/fuente")
    source_product_name: str = Field(..., max_length=500)
    price: decimal.Decimal = Field(..., max_digits=12, decimal_places=2)
    currency: str = Field(..., max_length=10)
    product_url: HttpUrl
    scraped_at: datetime = Field(..., description="Cuándo se obtuvo este precio")
    # Opcional: Añadir más campos como imagen, etc.
    # image_url: Optional[HttpUrl] = None

class SearchResponse(BaseModel):
    query: str = Field(..., description="Término de búsqueda original")
    results: List[SearchResultItem] = Field(..., description="Lista de precios encontrados")
    from_cache: bool = Field(default=False, description="Indica si los resultados vienen de la caché")
    message: Optional[str] = Field(None, description="Mensaje adicional (ej: 'Scraping en progreso')")
    job_id: Optional[int] = Field(None, description="ID del job de scraping si se inició uno nuevo")


# --- Modelos para Jobs de Scraping (Opcional pero útil) ---
class ScrapeJobBase(BaseModel):
    query_term: str = Field(..., max_length=255)
    # source_id es opcional, un job puede ser para todas las fuentes o una específica
    source_id: Optional[int] = Field(None, description="ID de la fuente específica a scrapear (si aplica)")
    status: str = Field(default='PENDING', max_length=50, description="Estado actual del job (PENDING, RUNNING, COMPLETED, FAILED)")

class ScrapeJobCreate(ScrapeJobBase):
    pass # Hereda los campos necesarios

class ScrapeJobUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=50)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class ScrapeJob(ScrapeJobBase):
    model_config = model_config
    job_id: int = Field(..., description="ID único del job")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None
    # Opcional: Incluir info de la fuente si source_id no es None
    source: Optional[Source] = None
