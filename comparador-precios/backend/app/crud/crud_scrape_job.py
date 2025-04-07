from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.db_models import ScrapeJobDB
from app.models.schemas import ScrapeJobCreate, ScrapeJobUpdate

class CRUDScrapeJob:
    def get(self, db: Session, job_id: int) -> Optional[ScrapeJobDB]:
        """
        Obtiene un job de scraping por su ID.
        """
        return db.query(ScrapeJobDB).filter(ScrapeJobDB.job_id == job_id).first()

    def get_multi_by_status(
        self, db: Session, *, status: str, skip: int = 0, limit: int = 100
    ) -> List[ScrapeJobDB]:
        """
        Obtiene jobs de scraping por estado.
        """
        return db.query(ScrapeJobDB).filter(ScrapeJobDB.status == status).offset(skip).limit(limit).all()

    def get_pending_for_query(self, db: Session, *, query_term: str) -> Optional[ScrapeJobDB]:
        """
        Busca si ya existe un job PENDIENTE o EN CURSO para una query específica.
        """
        return db.query(ScrapeJobDB).filter(
            ScrapeJobDB.query_term == query_term,
            ScrapeJobDB.status.in_(['PENDING', 'RUNNING'])
        ).first()


    def create(self, db: Session, *, obj_in: ScrapeJobCreate) -> ScrapeJobDB:
        """
        Crea un nuevo job de scraping.
        """
        db_obj = ScrapeJobDB(
            query_term=obj_in.query_term,
            source_id=obj_in.source_id,
            status=obj_in.status,
            # created_at es automático
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: ScrapeJobDB, obj_in: ScrapeJobUpdate
    ) -> ScrapeJobDB:
        """
        Actualiza un job de scraping existente.
        """
        update_data = obj_in.model_dump(exclude_unset=True) # Pydantic v2

        # Asegurarse de que las fechas se manejen correctamente si se proporcionan
        if 'started_at' in update_data and update_data['started_at'] is None:
            db_obj.started_at = None
        elif 'started_at' in update_data:
             db_obj.started_at = update_data['started_at']

        if 'completed_at' in update_data and update_data['completed_at'] is None:
            db_obj.completed_at = None
        elif 'completed_at' in update_data:
             db_obj.completed_at = update_data['completed_at']

        # Actualizar otros campos
        if 'status' in update_data:
            db_obj.status = update_data['status']
        if 'error_message' in update_data:
             db_obj.error_message = update_data['error_message']


        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def mark_as_running(self, db: Session, *, job_id: int) -> Optional[ScrapeJobDB]:
        """Marca un job como RUNNING."""
        db_obj = self.get(db, job_id=job_id)
        if db_obj and db_obj.status == 'PENDING':
            update_data = ScrapeJobUpdate(status='RUNNING', started_at=datetime.utcnow())
            return self.update(db=db, db_obj=db_obj, obj_in=update_data)
        return db_obj # Retorna el objeto aunque no se actualice

    def mark_as_completed(self, db: Session, *, job_id: int) -> Optional[ScrapeJobDB]:
        """Marca un job como COMPLETED."""
        db_obj = self.get(db, job_id=job_id)
        if db_obj and db_obj.status == 'RUNNING':
            update_data = ScrapeJobUpdate(status='COMPLETED', completed_at=datetime.utcnow())
            return self.update(db=db, db_obj=db_obj, obj_in=update_data)
        return db_obj

    def mark_as_failed(self, db: Session, *, job_id: int, error_message: str) -> Optional[ScrapeJobDB]:
        """Marca un job como FAILED."""
        db_obj = self.get(db, job_id=job_id)
        if db_obj and db_obj.status == 'RUNNING':
            update_data = ScrapeJobUpdate(
                status='FAILED',
                completed_at=datetime.utcnow(),
                error_message=error_message
            )
            return self.update(db=db, db_obj=db_obj, obj_in=update_data)
        return db_obj


    def remove(self, db: Session, *, job_id: int) -> Optional[ScrapeJobDB]:
        """
        Elimina un job de scraping por su ID.
        """
        obj = db.query(ScrapeJobDB).get(job_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

# Instancia del CRUD para ser importada
scrape_job = CRUDScrapeJob()
