from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, ForeignKey, JSON, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base # Importar Base declarativa desde session.py

class SourceDB(Base):
    __tablename__ = "sources"

    source_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    base_url = Column(String(255), nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relación uno-a-muchos con PriceDB
    prices = relationship("PriceDB", back_populates="source", cascade="all, delete-orphan")
    # Relación uno-a-muchos con ScrapeJobDB
    scrape_jobs = relationship("ScrapeJobDB", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SourceDB(source_id={self.source_id}, name='{self.name}')>"

class PriceDB(Base):
    __tablename__ = "prices"

    price_id = Column(Integer, primary_key=True, index=True)
    product_query_term = Column(String(255), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.source_id"), nullable=False, index=True)
    source_product_name = Column(String(500), nullable=False)
    # Usar Numeric para precisión decimal, ajustar precisión según necesidad
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), nullable=False, default='CLP')
    # Aumentar longitud si URLs son muy largas, considerar Text si es necesario
    product_url = Column(String(2048), nullable=False, unique=True, index=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    # JSONB es específico de PostgreSQL, usar JSON si se necesita compatibilidad más amplia
    attributes = Column(JSON, nullable=True)

    # Relación muchos-a-uno con SourceDB
    source = relationship("SourceDB", back_populates="prices")

    # Índices adicionales definidos explícitamente (aunque algunos ya están por index=True)
    __table_args__ = (
        Index('idx_price_query_source', 'product_query_term', 'source_id'),
    )

    def __repr__(self):
        return f"<PriceDB(price_id={self.price_id}, name='{self.source_product_name}', price={self.price})>"


class ScrapeJobDB(Base):
    __tablename__ = "scrape_jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    query_term = Column(String(255), nullable=False, index=True)
    # Permitir NULL si es un job general, o FK si es para una fuente específica
    source_id = Column(Integer, ForeignKey("sources.source_id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default='PENDING', index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    error_message = Column(Text, nullable=True)

    # Relación muchos-a-uno con SourceDB
    source = relationship("SourceDB", back_populates="scrape_jobs")

    def __repr__(self):
        return f"<ScrapeJobDB(job_id={self.job_id}, query='{self.query_term}', status='{self.status}')>"

# Nota: La tabla 'products' se omitió según el DDL inicial,
# pero podría añadirse aquí si se decide normalizar productos.
