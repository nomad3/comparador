from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.db_models import SourceDB
from app.models.schemas import SourceCreate, SourceUpdate

class CRUDSource:
    def get(self, db: Session, source_id: int) -> Optional[SourceDB]:
        """
        Obtiene una fuente por su ID.
        """
        return db.query(SourceDB).filter(SourceDB.source_id == source_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[SourceDB]:
        """
        Obtiene una fuente por su nombre.
        """
        return db.query(SourceDB).filter(SourceDB.name == name).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[SourceDB]:
        """
        Obtiene una lista de fuentes con paginación.
        """
        return db.query(SourceDB).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: SourceCreate) -> SourceDB:
        """
        Crea una nueva fuente.
        """
        db_obj = SourceDB(
            name=obj_in.name,
            base_url=str(obj_in.base_url) # Convertir HttpUrl a string para DB
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: SourceDB, obj_in: SourceUpdate
    ) -> SourceDB:
        """
        Actualiza una fuente existente.
        """
        update_data = obj_in.model_dump(exclude_unset=True) # Usar model_dump en Pydantic v2
        if 'base_url' in update_data:
             update_data['base_url'] = str(update_data['base_url']) # Convertir HttpUrl

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, source_id: int) -> Optional[SourceDB]:
        """
        Elimina una fuente por su ID.
        """
        obj = db.query(SourceDB).get(source_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

# Instancia del CRUD para ser importada
source = CRUDSource()
