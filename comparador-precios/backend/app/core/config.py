import os
from pydantic_settings import BaseSettings
from typing import List, Union, Optional
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from the backend directory
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Comparador Precios API"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Base de Datos PostgreSQL
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "comparador_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "supersecretpassword")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "comparador_db")
    # SQLAlchemy Database URL (usando psycopg2 driver sync)
    DATABASE_URL: str = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    # Opcional: Async driver URL si usas SQLAlchemy async features
    # ASYNC_DATABASE_URL: str = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "cache")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    CACHE_EXPIRATION_SECONDS: int = int(os.getenv("CACHE_EXPIRATION_SECONDS", 3600)) # 1 hora por defecto

    # CORS
    # Acepta una string separada por comas o una lista de strings
    BACKEND_CORS_ORIGINS: List[str] = [
        origin.strip() for origin in os.getenv("BACKEND_CORS_ORIGINS", "").split(',') if origin
    ]
    # Si BACKEND_CORS_ORIGINS está vacío en .env, permite todo en desarrollo (¡cuidado en prod!)
    if not BACKEND_CORS_ORIGINS and os.getenv("ENVIRONMENT", "development") == "development":
        BACKEND_CORS_ORIGINS = ["*"]

    # Scraping settings
    SCRAPER_TIMEOUT_SECONDS: int = 30 # Timeout para requests HTTP de scraping
    SCRAPER_DEFAULT_HEADERS: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    class Config:
        case_sensitive = True
        # Especifica que el .env está en el directorio padre (backend/)
        # Esto es redundante si ya usamos load_dotenv arriba, pero es buena práctica
        # env_file = '.env'
        # env_file_encoding = 'utf-8'

settings = Settings()

# Imprimir orígenes CORS para depuración al inicio (opcional)
# from loguru import logger
# logger.debug(f"CORS Origins configurados: {settings.BACKEND_CORS_ORIGINS}")
