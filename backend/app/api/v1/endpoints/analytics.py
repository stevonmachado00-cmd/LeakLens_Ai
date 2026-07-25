from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import AnalyticsResponse

router = APIRouter()


@router.get("/dashboard", response_model=AnalyticsResponse)
def dashboard_analytics(*, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = AnalyticsService.dashboard(db, user_id=current_user.id)
    # Return dataclass as dict
    return {
        "overview": result.overview,
        "spending_by_category": result.spending_by_category,
        "monthly_trend": result.monthly_trend,
        "top_subscriptions": result.top_subscriptions,
        "billing_distribution": result.billing_distribution,
        "recent_subscriptions": result.recent_subscriptions,
        "top_costly_subscriptions": result.top_costly_subscriptions,
        "recommendations": result.recommendations,
    }
