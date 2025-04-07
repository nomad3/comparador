import asyncio
from urllib.parse import quote_plus
from bs4 import BeautifulSoup, Tag
from typing import List, Optional
import decimal
import json # Falabella might use JSON-LD or embedded JSON

from .base_scraper import BaseScraper, ScraperInput, ScrapedData

class FalabellaScraper(BaseScraper):
    """Scraper específico para Falabella Chile."""

    async def _build_search_url(self) -> str:
        """Construye la URL de búsqueda para Falabella Chile."""
        # Ejemplo: https://www.falabella.com/falabella-cl/search?Ntt=laptop%20gamer
        query_encoded = quote_plus(self.input.query.lower())
        search_url = f"{self.input.base_url}/search?Ntt={query_encoded}"
        self.logger.info(f"Construida URL de búsqueda: {search_url}")
        return search_url

    async def _parse_results(self, content: str) -> List[ScrapedData]:
        """Parsea el HTML de resultados de búsqueda de Falabella."""
        soup = BeautifulSoup(content, 'html.parser')
        results: List[ScrapedData] = []

        # Falabella a menudo usa divs con IDs específicos o clases como 'search-results' o 'product-grid'
        # Selector para los contenedores de productos individuales. ¡¡PROPENSO A CAMBIOS!!
        # Intentar con clases comunes como 'product-card', 'pod', 'product-item'
        items = soup.select('div.pod, div.product-card, div.product-item') # Probar varios

        self.logger.info(f"Encontrados {len(items)} elementos HTML con selectores de item.")

        if not items:
             # A veces los datos están en un script JSON-LD o similar
             script_ld_json = soup.find('script', type='application/ld+json')
             if script_ld_json:
                 self.logger.info("Intentando parsear datos desde script ld+json.")
                 try:
                     data = json.loads(script_ld_json.string)
                     # El formato de JSON-LD varía, buscar una lista de productos (ItemList)
                     if data.get('@type') == 'ItemList' and 'itemListElement' in data:
                         for item_data in data['itemListElement']:
                             # Extraer datos del JSON-LD (la estructura puede variar)
                             if item_data.get('@type') == 'Product':
                                 name = item_data.get('name')
                                 url = item_data.get('url')
                                 offers = item_data.get('offers')
                                 price = None
                                 if offers and isinstance(offers, dict) and offers.get('@type') == 'Offer':
                                     price_str = offers.get('price')
                                     if price_str:
                                         price = self._extract_price(str(price_str))

                                 if name and price and url:
                                     results.append(ScrapedData(
                                         source_product_name=self._clean_text(name),
                                         price=price,
                                         product_url=url # Asumir que la URL es válida
                                     ))
                         self.logger.info(f"Parseados {len(results)} items desde JSON-LD.")
                         return results # Salir si se encontraron datos en JSON-LD
                     else:
                          self.logger.warning("Script ld+json encontrado pero no tiene formato ItemList esperado.")
                 except json.JSONDecodeError:
                     self.logger.error("Error al decodificar script ld+json.")
                 except Exception as e:
                     self.logger.exception(f"Error inesperado parseando JSON-LD: {e}")


        # Si no hay JSON-LD o falla, continuar con parseo HTML
        for item in items:
            try:
                name = self._extract_name(item)
                price = self._extract_price_falabella(item)
                url = self._extract_url(item)

                if name and price and url:
                    # Asegurarse que la URL sea absoluta
                    if not url.startswith('http'):
                        base = self.input.base_url.split('/search')[0] # Obtener base real
                        url = f"{base}{url}" if url.startswith('/') else f"{base}/{url}"

                    scraped_item = ScrapedData(
                        source_product_name=name,
                        price=price,
                        product_url=url,
                    )
                    results.append(scraped_item)
                else:
                     self.logger.warning(f"Item HTML omitido por falta de datos (Nombre: {name is not None}, Precio: {price is not None}, URL: {url is not None})")

            except Exception as e:
                self.logger.exception(f"Error procesando un item de resultado HTML: {e}")

        return results

    def _extract_name(self, item: Tag) -> Optional[str]:
        """Extrae el nombre del producto del item HTML."""
        # Selectores comunes para el nombre/título en Falabella. ¡¡PROPENSO A CAMBIOS!!
        name_tag = item.select_one('b.pod-title, span.copy10, div.product-card__name, a.product-item__name')
        if name_tag:
            return self._clean_text(name_tag.text)
        # Intentar buscar por atributo 'title' en algún enlace
        link_with_title = item.find('a', title=True)
        if link_with_title:
             return self._clean_text(link_with_title['title'])
        self.logger.warning("No se encontró tag de nombre con selectores comunes.")
        return None

    def _extract_price_falabella(self, item: Tag) -> Optional[decimal.Decimal]:
        """Extrae el precio del producto del item HTML."""
        # Falabella puede tener varios precios (normal, oferta, con tarjeta). Intentar obtener el más prominente (oferta/internet).
        # ¡¡PROPENSO A CAMBIOS!!
        # Precio de oferta/internet
        price_tag = item.select_one('span.copy1, li.price-best span.copy1, div.product-card__price, span.product-item__price')
        if price_tag:
            price_str = self._clean_text(price_tag.text)
            # A veces el precio incluye '.--' al final, quitarlo
            price_str = price_str.split(".--")[0]
            extracted_price = self._extract_price(price_str)
            if extracted_price:
                return extracted_price

        # Si no hay precio de oferta, buscar precio normal
        price_tag_normal = item.select_one('li.price-original span.copy3')
        if price_tag_normal:
             price_str = self._clean_text(price_tag_normal.text)
             price_str = price_str.split(".--")[0]
             extracted_price = self._extract_price(price_str)
             if extracted_price:
                 return extracted_price

        self.logger.warning("No se encontró tag de precio con selectores comunes.")
        return None

    def _extract_url(self, item: Tag) -> Optional[str]:
        """Extrae la URL del producto del item HTML."""
        # La URL suele estar en el tag <a> principal del producto.
        # ¡¡PROPENSO A CAMBIOS!!
        url_tag = item.select_one('a.pod-link, div.product-card__name a, a.product-item__name, a.product-item__image')
        if url_tag and url_tag.has_attr('href'):
            return url_tag['href']
        # A veces el contenedor principal es el enlace
        if item.name == 'a' and item.has_attr('href'):
             return item['href']
        self.logger.warning("No se encontró tag de URL con selectores comunes.")
        return None


# Ejemplo de uso (para pruebas locales)
async def main():
    test_input = ScraperInput(
        query="smartphone",
        source_id=2, # ID ficticio
        source_name="Falabella Chile",
        base_url="https://www.falabella.com/falabella-cl"
    )
    scraper = FalabellaScraper(test_input)
    results = await scraper.scrape()
    if results:
        print(f"Resultados encontrados para '{test_input.query}':")
        for res in results:
            print(f"- {res.source_product_name} | ${res.price} | {res.product_url}")
    else:
        print(f"No se encontraron resultados para '{test_input.query}'.")

if __name__ == "__main__":
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    asyncio.run(main())
