from fastapi import APIRouter

from app.api.v1.endpoints import search

# Create the main router for API version 1
api_router = APIRouter()

# Include the search endpoint router
# All routes defined in search.router will be prefixed with /search
api_router.include_router(search.router, prefix="/search", tags=["Search & Scrape"])

# Future endpoints can be included here:
# from app.api.v1.endpoints import sources, jobs
# api_router.include_router(sources.router, prefix="/sources", tags=["Sources"])
# api_router.include_router(jobs.router, prefix="/jobs", tags=["Scraping Jobs"])
