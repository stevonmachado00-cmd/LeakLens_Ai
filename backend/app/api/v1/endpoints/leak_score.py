from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.leak_score import LeakScoreResponse
from app.services.leak_score_service import LeakScoreService

router = APIRouter()


@router.get("", response_model=LeakScoreResponse)
def get_leak_score(*, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Compute leak score dynamically for the current user."""
    result = LeakScoreService.calculate_score(db, user_id=current_user.id)
    # Convert dataclass to response model fields
    return {
        "score": result.score,
        "risk_level": result.risk_level,
        "monthly_spend": result.monthly_spend,
        "yearly_spend": result.yearly_spend,
        "potential_monthly_savings": result.potential_monthly_savings,
        "potential_yearly_savings": result.potential_yearly_savings,
        "active_subscriptions": result.active_subscriptions,
        "duplicate_subscriptions": result.duplicate_subscriptions,
        "high_cost_subscriptions": result.high_cost_subscriptions,
        "recommendation_count": result.recommendation_count,
        "summary": result.summary,
        "breakdown": result.breakdown,
    }
