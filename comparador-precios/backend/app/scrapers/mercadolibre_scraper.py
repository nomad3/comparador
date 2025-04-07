import asyncio
from urllib.parse import quote_plus
from bs4 import BeautifulSoup, Tag
from typing import List, Optional
import decimal

from .base_scraper import BaseScraper, ScraperInput, ScrapedData

class MercadoLibreScraper(BaseScraper):
    """Scraper específico para MercadoLibre Chile."""

    async def _build_search_url(self) -> str:
        """Construye la URL de búsqueda para MercadoLibre Chile."""
        # Ejemplo: https://listado.mercadolibre.cl/laptop-gamer#D[A:laptop%20gamer]
        # El formato parece ser: base_url/query_encoded#D[A:query_encoded]
        # O más simple: https://listado.mercadolibre.cl/QUERY
        query_encoded = quote_plus(self.input.query.lower())
        # Usaremos el formato más simple que suele funcionar
        search_url = f"{self.input.base_url}/listado?search={query_encoded}"
        # Alternativa (formato antiguo?):
        # search_url = f"{self.input.base_url}/{query_encoded}#D[A:{query_encoded}]"
        self.logger.info(f"Construida URL de búsqueda: {search_url}")
        return search_url

    async def _parse_results(self, content: str) -> List[ScrapedData]:
        """Parsea el HTML de resultados de búsqueda de MercadoLibre."""
        soup = BeautifulSoup(content, 'html.parser')
        results: List[ScrapedData] = []

        # Selector principal para cada item de producto en la lista
        # ¡¡ESTE SELECTOR ES MUY PROPENSO A CAMBIOS!! Inspeccionar el HTML real es crucial.
        # Intentemos con selectores comunes para la lista de resultados.
        # Puede ser 'ui-search-layout__item', 'andes-card', etc.
        # Usaremos uno común, pero podría necesitar ajuste.
        items = soup.select('li.ui-search-layout__item, div.ui-search-result__wrapper') # Intentar ambos

        self.logger.info(f"Encontrados {len(items)} elementos HTML con selectores de item.")

        if not items:
             # Intentar otro selector común si el primero falla
             items = soup.select('div.andes-card.ui-search-result')
             self.logger.info(f"Intentando selector alternativo, encontrados {len(items)} elementos.")

        for item in items:
            try:
                name = self._extract_name(item)
                price = self._extract_price_ml(item)
                url = self._extract_url(item)

                if name and price and url:
                    # Crear instancia de ScrapedData (validación Pydantic ocurrirá después)
                    scraped_item = ScrapedData(
                        source_product_name=name,
                        price=price,
                        product_url=url,
                        # currency se asume CLP por defecto en ScrapedData
                    )
                    results.append(scraped_item)
                else:
                    self.logger.warning(f"Item omitido por falta de datos (Nombre: {name is not None}, Precio: {price is not None}, URL: {url is not None})")

            except Exception as e:
                self.logger.exception(f"Error procesando un item de resultado: {e}")
                # self.logger.error(f"Error procesando un item: {e}. Item HTML: {item.prettify()[:500]}...") # Loggear HTML puede ser útil para debug

        return results

    def _extract_name(self, item: Tag) -> Optional[str]:
        """Extrae el nombre del producto del item HTML."""
        # Selector común para el título/nombre del producto
        # ¡¡PROPENSO A CAMBIOS!!
        name_tag = item.select_one('h2.ui-search-item__title, a.ui-search-item__group__element.ui-search-link__title')
        if name_tag:
            return self._clean_text(name_tag.text)
        self.logger.warning("No se encontró tag de nombre con selectores comunes.")
        return None

    def _extract_price_ml(self, item: Tag) -> Optional[decimal.Decimal]:
        """Extrae el precio del producto del item HTML."""
        # Selector común para el precio. Puede estar dentro de spans con clases específicas.
        # ¡¡PROPENSO A CAMBIOS!!
        price_tag = item.select_one('span.andes-money-amount__fraction, span.price-tag-fraction')
        # A veces hay centavos: span.andes-money-amount__cents, span.price-tag-cents
        cents_tag = item.select_one('span.andes-money-amount__cents, span.price-tag-cents')

        if price_tag:
            price_str = price_tag.text
            if cents_tag:
                 # Asumimos formato chileno con coma decimal si hay centavos
                 price_str = f"{price_str},{cents_tag.text}"
            else:
                 # Si no hay centavos, podría ser un entero
                 price_str = f"{price_str}"

            # Usar el helper de la clase base para limpiar y convertir
            return self._extract_price(price_str) # _extract_price maneja limpieza de puntos, $, etc.

        self.logger.warning("No se encontró tag de precio con selectores comunes.")
        return None

    def _extract_url(self, item: Tag) -> Optional[str]:
        """Extrae la URL del producto del item HTML."""
        # La URL suele estar en un tag <a> que envuelve la imagen o el título.
        # ¡¡PROPENSO A CAMBIOS!!
        url_tag = item.select_one('a.ui-search-link, a.ui-search-result__content') # Intentar varios selectores comunes
        if url_tag and url_tag.has_attr('href'):
            url = url_tag['href']
            # A veces las URLs son relativas, aunque en ML suelen ser absolutas o trackeadas.
            # Limpiar parámetros de tracking si es necesario (ej: ?searchVariation=...)
            url_cleaned = url.split('?')[0] # Simple limpieza, puede ser más compleja
            return url_cleaned # Devolver URL limpia
        self.logger.warning("No se encontró tag de URL con selectores comunes.")
        return None

# Ejemplo de uso (para pruebas locales si se ejecuta directamente)
async def main():
    test_input = ScraperInput(
        query="laptop gamer",
        source_id=1, # ID ficticio para prueba
        source_name="MercadoLibre Chile",
        base_url="https://www.mercadolibre.cl"
    )
    scraper = MercadoLibreScraper(test_input)
    results = await scraper.scrape()
    if results:
        print(f"Resultados encontrados para '{test_input.query}':")
        for res in results:
            print(f"- {res.source_product_name} | ${res.price} | {res.product_url}")
    else:
        print(f"No se encontraron resultados para '{test_input.query}'.")

if __name__ == "__main__":
    # Configurar logger básico si se ejecuta standalone
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    asyncio.run(main())
