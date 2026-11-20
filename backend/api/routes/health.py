"""
api/routes/health.py — Health check endpoint

GET /health

Returns the API status and whether all three ML models are loaded.
Used by monitoring tools and the React frontend to verify the backend is ready.
"""

from fastapi import APIRouter

from models.loader import get_model_registry
from models.schemas import HealthResponse, ModelStatus

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    description="Returns `status: ok` and whether all ML models are loaded and ready.",
)
async def health_check() -> HealthResponse:
    registry = get_model_registry()
    status = registry.status()
    return HealthResponse(
        status="ok" if registry.all_loaded else "degraded",
        models_loaded=ModelStatus(**status),
    )
