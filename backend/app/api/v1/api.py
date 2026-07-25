from fastapi import APIRouter
from app.api.v1.endpoints import auth, statements, subscriptions, recommendations, leak_score, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(statements.router, prefix="/statements", tags=["statements"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(leak_score.router, prefix="/leak-score", tags=["leak-score"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
