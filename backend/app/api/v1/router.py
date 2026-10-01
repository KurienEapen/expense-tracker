from fastapi import APIRouter
from app.api.v1.endpoints import health, ingest, heartbeat, parser, transactions, categories, rules, budgets, analytics, tags

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ingest.router, tags=["Ingest"])
api_router.include_router(heartbeat.router, tags=["Heartbeat"])
api_router.include_router(parser.router, prefix="/parser", tags=["Parser"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules"])
api_router.include_router(rules.router, prefix="/merchant-rules", tags=["Rules"])
api_router.include_router(budgets.router, prefix="/budgets", tags=["Budgets"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(analytics.router, prefix="/insights", tags=["Analytics"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
