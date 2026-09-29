from fastapi import APIRouter
from app.api.v1.endpoints import health, ingest, heartbeat

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ingest.router, tags=["Ingest"])
api_router.include_router(heartbeat.router, tags=["Heartbeat"])
