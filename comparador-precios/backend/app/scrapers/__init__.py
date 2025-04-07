# Web scraping modules
from .base_scraper import BaseScraper, ScraperInput, ScrapedData
from .mercadolibre_scraper import MercadoLibreScraper
from .falabella_scraper import FalabellaScraper
# Import other scrapers here

# Dictionary mapping source names (from DB) to scraper classes
# Ensure the names match exactly what's in the 'sources' table
SCRAPER_MAPPING = {
    "MercadoLibre Chile": MercadoLibreScraper,
    "Falabella Chile": FalabellaScraper,
    # "Paris.cl": ParisScraper, # Add when implemented
}

__all__ = ["BaseScraper", "ScraperInput", "ScrapedData", "SCRAPER_MAPPING"]
