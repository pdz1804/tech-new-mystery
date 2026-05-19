"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import configure_middleware
from app.integrations.llm_client import get_llm_client, shutdown_llm
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    configure_logging()
    logger.info("FastAPI app starting up")

    # Initialize Celery
    try:
        celery_app.conf.update(task_track_started=True, task_send_sent_event=True)
        logger.info(f"Celery broker: {settings.celery_broker_url}")
        logger.info(f"Celery result backend: {settings.celery_result_backend}")
    except Exception as e:
        logger.error(f"Failed to initialize Celery: {e}")

    # Initialize LLM client
    try:
        llm_client = await get_llm_client()
        is_healthy = await llm_client.health_check()
        if is_healthy:
            logger.info(f"LLM provider '{settings.llm_provider}' initialized")
        else:
            logger.warning(f"LLM provider '{settings.llm_provider}' health check failed")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM client: {e}")

    yield

    # Shutdown
    logger.info("FastAPI app shutting down")
    await shutdown_llm()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Configure middleware
    configure_middleware(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(v1_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    # Celery health check endpoint
    @app.get("/health/celery")
    async def celery_health_check():
        """Check Celery worker availability."""
        try:
            # Ping Celery to check if broker is available
            celery_app.control.inspect().ping()
            return {"status": "ok", "service": "celery"}
        except Exception as e:
            logger.warning(f"Celery health check failed: {e}")
            return {"status": "error", "service": "celery", "error": str(e)}

    # LLM health check endpoint
    @app.get("/health/llm")
    async def llm_health_check():
        """Check LLM provider availability."""
        try:
            llm_client = await get_llm_client()
            is_healthy = await llm_client.health_check()
            return {
                "status": "ok" if is_healthy else "degraded",
                "service": "llm",
                "provider": settings.llm_provider,
            }
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return {
                "status": "error",
                "service": "llm",
                "provider": settings.llm_provider,
                "error": str(e),
            }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
