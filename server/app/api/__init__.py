from fastapi import APIRouter
from . import health, v1

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(v1.router, prefix="/v1")
