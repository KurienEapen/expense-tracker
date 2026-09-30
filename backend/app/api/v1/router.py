from fastapi import APIRouter
from app.api.v1.endpoints import health, ingest, heartbeat, parser, transactions, categories

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ingest.router, tags=["Ingest"])
api_router.include_router(heartbeat.router, tags=["Heartbeat"])
api_router.include_router(parser.router, prefix="/parser", tags=["Parser"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
