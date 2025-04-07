import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.api.v1.api import api_router # Import the main v1 router
from app.db.session import engine, init_db # Import engine for check, init_db if needed
from app.core.redis_client import init_redis_pool, close_redis_pool, get_redis_client

# --- Loguru Configuration ---
# Remove default handler and add a formatted one
logger.remove()
logger.add(
    sys.stderr, # Log to stderr
    level=settings.LOG_LEVEL.upper(),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)
# Optional: Add file logging
# logger.add("logs/backend_{time}.log", rotation="1 day", retention="7 days", level="INFO")

logger.info("Logger configured.")
logger.info(f"Log Level: {settings.LOG_LEVEL.upper()}")

# --- Application Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    - Initializes Redis pool on startup.
    - Closes Redis pool on shutdown.
    - Checks DB connection.
    """
    logger.info("--- Application Startup ---")
    # Initialize Redis Pool
    await init_redis_pool()
    redis_conn = await get_redis_client()
    if not redis_conn:
        logger.critical("Redis connection FAILED. Application might not work correctly.")
        # Depending on criticality, you might want to prevent startup
        # raise RuntimeError("Failed to connect to Redis")
    else:
        logger.info("Redis connection pool initialized successfully.")

    # Check DB connection (optional but good practice)
    if engine is None:
        logger.critical("Database engine FAILED to initialize. Application might not work correctly.")
        # raise RuntimeError("Failed to initialize database engine")
    else:
        try:
            # Try to connect to check
            with engine.connect() as connection:
                logger.info("Database connection verified successfully.")
        except Exception as e:
            logger.critical(f"Database connection check FAILED: {e}")
            # raise RuntimeError("Failed to connect to the database")

    # Optional: Initialize DB (create tables) if not using migrations like Alembic
    # Be careful using this in production if you manage migrations separately.
    # init_db()

    logger.info("--- Application Ready ---")
    yield # Application runs here
    logger.info("--- Application Shutdown ---")
    # Close Redis Pool
    await close_redis_pool()
    logger.info("Redis connection pool closed.")
    logger.info("--- Application Shutdown Complete ---")


# --- FastAPI Application Instantiation ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # URL for OpenAPI spec
    docs_url=f"{settings.API_V1_STR}/docs", # URL for Swagger UI
    redoc_url=f"{settings.API_V1_STR}/redoc", # URL for ReDoc
    version="0.1.0", # Project version
    lifespan=lifespan # Use the lifespan context manager
)

# --- CORS Middleware Configuration ---
if settings.BACKEND_CORS_ORIGINS:
    logger.info(f"Configuring CORS for origins: {settings.BACKEND_CORS_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.BACKEND_CORS_ORIGINS if origin], # Handle potential empty strings
        allow_credentials=True,
        allow_methods=["*"], # Allow all standard methods
        allow_headers=["*"], # Allow all headers
    )
else:
    # Log a warning if CORS is not configured, as it might block frontend requests
    logger.warning("CORS origins not configured (BACKEND_CORS_ORIGINS is empty). Frontend requests might be blocked by the browser.")


# --- Include API Routers ---
# Include the main v1 router, prefixing all its routes with /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint providing basic application info.
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": app.docs_url,
        "redoc_url": app.redoc_url
        }

# --- Health Check Endpoint ---
@app.get("/health", tags=["Health"])
async def health_check(
    redis_client: redis.Redis = Depends(deps.get_redis_client) # Use dependency to check Redis
):
    """
    Performs health checks on essential services (DB, Cache).
    """
    db_status = "ok"
    redis_status = "ok"
    status_code = status.HTTP_200_OK

    # Check DB (Engine initialization)
    if engine is None:
        db_status = "error: engine not initialized"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        # Try a simple query
        try:
            with engine.connect() as connection:
                # connection.execute(text("SELECT 1")) # Simple query
                pass # Just connecting is often enough
        except Exception as e:
            logger.error(f"Health Check: DB connection error - {e}")
            db_status = f"error: connection failed ({e.__class__.__name__})"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Check Redis (already checked by dependency, but can ping again)
    try:
        await redis_client.ping()
    except Exception as e:
        logger.error(f"Health Check: Redis ping error - {e}")
        redis_status = f"error: ping failed ({e.__class__.__name__})"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    response_detail = {"status": "ok" if status_code == 200 else "error", "database": db_status, "cache": redis_status}

    if status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status_code, detail=response_detail)

    return response_detail


# --- Optional: Add global exception handlers ---
# from fastapi import Request, status
# from fastapi.responses import JSONResponse
# @app.exception_handler(Exception) # Catch-all handler (use with caution)
# async def generic_exception_handler(request: Request, exc: Exception):
#     logger.exception(f"Unhandled exception for request {request.method} {request.url}: {exc}")
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "An unexpected internal server error occurred."},
#     )

logger.info("FastAPI application instance created.")

# Note: Uvicorn will run this app instance when started.
# Example: uvicorn app.main:app --reload
