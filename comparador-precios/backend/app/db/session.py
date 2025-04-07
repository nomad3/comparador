from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from loguru import logger

# Crear el engine de SQLAlchemy
# pool_pre_ping=True ayuda a manejar conexiones que pueden haber sido cerradas por la DB
try:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False) # echo=True para debug SQL
    # Probar la conexión inmediatamente (opcional pero recomendado)
    with engine.connect() as connection:
        logger.info(f"Conexión a PostgreSQL ({settings.POSTGRES_DB}@{settings.POSTGRES_SERVER}) establecida exitosamente.")
except Exception as e:
    logger.error(f"Error al crear el engine o conectar a PostgreSQL: {e}")
    logger.error(f"URL de conexión usada: {settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, '********')}")
    # Podrías lanzar una excepción aquí para detener la app si la DB es crítica al inicio
    engine = None

# Crear una fábrica de sesiones configurada
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Fábrica de sesiones SQLAlchemy (SessionLocal) creada.")
else:
    SessionLocal = None
    logger.error("SessionLocal no pudo ser creada porque el engine de DB falló.")

# Crear una clase Base para que los modelos la hereden
Base = declarative_base()

# Función para crear tablas (Usar con precaución, preferir Alembic para migraciones)
def init_db():
    if engine and Base.metadata.tables:
        logger.info("Intentando crear tablas en la base de datos (si no existen)...")
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Tablas verificadas/creadas exitosamente usando Base.metadata.create_all().")
        except Exception as e:
            logger.error(f"Error al ejecutar Base.metadata.create_all(): {e}")
    elif not engine:
         logger.error("No se pueden crear tablas porque el engine de DB no está disponible.")
    else:
         logger.warning("No hay tablas definidas en Base.metadata para crear.")

# Nota: La dependencia get_db se definirá en api/deps.py para evitar importaciones circulares.
