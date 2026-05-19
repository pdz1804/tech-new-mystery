"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.articles.router import router as articles_router
from app.api.v1.sources.router import router as sources_router
from app.api.v1.search.router import router as search_router
from app.api.v1.user.router import router as user_router
from app.api.v1.comments.router import router as comments_router
from app.api.v1.trending.router import router as trending_router
from app.api.v1.admin.router import router as admin_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router)
router.include_router(articles_router)
router.include_router(sources_router)
router.include_router(search_router)
router.include_router(user_router)
router.include_router(comments_router)
router.include_router(trending_router)
router.include_router(admin_router)
