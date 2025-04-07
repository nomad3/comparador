from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.db_models import PriceDB, SourceDB
from app.models.schemas import PriceCreate, PriceUpdate

class CRUDPrice:
    def get(self, db: Session, price_id: int) -> Optional[PriceDB]:
        """
        Obtiene un precio por su ID.
        """
        return db.query(PriceDB).filter(PriceDB.price_id == price_id).first()

    def get_by_url(self, db: Session, product_url: str) -> Optional[PriceDB]:
        """
        Obtiene un precio por la URL única del producto en la fuente.
        """
        return db.query(PriceDB).filter(PriceDB.product_url == product_url).first()

    def get_multi_by_query(
        self,
        db: Session,
        *,
        query_term: str,
        skip: int = 0,
        limit: int = 100,
        min_scraped_at: Optional[datetime] = None,
        include_source: bool = False
    ) -> List[PriceDB]:
        """
        Obtiene una lista de precios para un término de búsqueda específico,
        opcionalmente filtrando por fecha mínima de scraping y cargando la fuente.
        """
        query = db.query(PriceDB).filter(PriceDB.product_query_term == query_term)

        if min_scraped_at:
            query = query.filter(PriceDB.scraped_at >= min_scraped_at)

        if include_source:
            # Carga ansiosa (eager loading) de la relación 'source' para evitar N+1 queries
            query = query.options(joinedload(PriceDB.source))

        return query.order_by(PriceDB.price.asc()).offset(skip).limit(limit).all()


    def create_or_update(self, db: Session, *, obj_in: PriceCreate) -> PriceDB:
        """
        Crea un nuevo precio o actualiza uno existente si la URL del producto ya existe.
        Esto es útil para evitar duplicados al hacer scraping repetidamente.
        """
        # Convertir HttpUrl a string antes de buscar/crear
        product_url_str = str(obj_in.product_url)

        db_obj = self.get_by_url(db, product_url=product_url_str)
        if db_obj:
            # Actualizar el precio existente
            # Solo actualizamos campos que cambian frecuentemente (precio, atributos, scraped_at)
            db_obj.price = obj_in.price
            db_obj.attributes = obj_in.attributes
            db_obj.source_product_name = obj_in.source_product_name # Nombre puede cambiar
            db_obj.scraped_at = datetime.utcnow() # Actualizar timestamp
            # No actualizamos source_id ni product_query_term aquí
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        else:
            # Crear nuevo registro de precio
            new_db_obj = PriceDB(
                product_query_term=obj_in.product_query_term,
                source_id=obj_in.source_id,
                source_product_name=obj_in.source_product_name,
                price=obj_in.price,
                currency=obj_in.currency,
                product_url=product_url_str, # Guardar como string
                attributes=obj_in.attributes,
                # scraped_at se establece por defecto en el modelo DB
            )
            db.add(new_db_obj)
            db.commit()
            db.refresh(new_db_obj)
            return new_db_obj

    def create_multi(self, db: Session, *, objs_in: List[PriceCreate]) -> List[PriceDB]:
        """
        Crea o actualiza múltiples precios. Más eficiente que llamar a create_or_update en bucle.
        """
        created_or_updated = []
        urls_in_batch = {str(p.product_url) for p in objs_in}

        # 1. Buscar precios existentes para las URLs del batch
        existing_prices_dict = {
            p.product_url: p
            for p in db.query(PriceDB).filter(PriceDB.product_url.in_(urls_in_batch)).all()
        }

        new_prices_to_add = []
        for obj_in in objs_in:
            product_url_str = str(obj_in.product_url)
            db_obj = existing_prices_dict.get(product_url_str)

            if db_obj:
                # Actualizar existente (similar a create_or_update)
                db_obj.price = obj_in.price
                db_obj.attributes = obj_in.attributes
                db_obj.source_product_name = obj_in.source_product_name
                db_obj.scraped_at = datetime.utcnow()
                # No es necesario db.add() aquí si el objeto ya está en la sesión
                created_or_updated.append(db_obj) # Añadir a la lista de resultados
            else:
                # Preparar nuevo objeto para añadir
                new_db_obj = PriceDB(
                    product_query_term=obj_in.product_query_term,
                    source_id=obj_in.source_id,
                    source_product_name=obj_in.source_product_name,
                    price=obj_in.price,
                    currency=obj_in.currency,
                    product_url=product_url_str,
                    attributes=obj_in.attributes,
                )
                new_prices_to_add.append(new_db_obj)

        # 2. Añadir todos los nuevos precios en bloque
        if new_prices_to_add:
            db.add_all(new_prices_to_add)

        # 3. Commit de todos los cambios (actualizaciones y nuevas inserciones)
        db.commit()

        # 4. Refrescar los nuevos objetos para obtener IDs y valores por defecto
        for new_obj in new_prices_to_add:
            db.refresh(new_obj)
            created_or_updated.append(new_obj) # Añadir a la lista de resultados

        return created_or_updated


    def remove_old_prices_by_query(self, db: Session, *, query_term: str, days_old: int) -> int:
        """
        Elimina precios antiguos para un término de búsqueda específico.
        Retorna el número de registros eliminados.
        """
        threshold_date = datetime.utcnow() - timedelta(days=days_old)
        num_deleted = db.query(PriceDB).filter(
            PriceDB.product_query_term == query_term,
            PriceDB.scraped_at < threshold_date
        ).delete(synchronize_session=False) # Importante para delete en bloque
        db.commit()
        return num_deleted

# Instancia del CRUD para ser importada
price = CRUDPrice()
