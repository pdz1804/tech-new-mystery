"""News sources endpoints."""

from fastapi import APIRouter, Depends

from app.api.dependencies import require_admin, get_source_service
from app.api.v1.sources.schemas import NewsSourceResponse, CreateNewsSourceRequest
from app.services.source_service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=dict)
async def list_sources(
    service: SourceService = Depends(get_source_service),
) -> dict:
    """List all news sources."""
    sources = await service.list_sources()
    return {"success": True, "data": sources}


@router.get("/{source_id}", response_model=dict)
async def get_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
) -> dict:
    """Get a specific news source."""
    source = await service.get_source(source_id)
    return {"success": True, "data": source}


@router.post("", response_model=dict, status_code=201)
async def create_source(
    payload: CreateNewsSourceRequest,
    _: dict = Depends(require_admin),
    service: SourceService = Depends(get_source_service),
) -> dict:
    """Create a new news source (admin only)."""
    source = await service.create_source(payload.model_dump())
    return {"success": True, "data": source}
