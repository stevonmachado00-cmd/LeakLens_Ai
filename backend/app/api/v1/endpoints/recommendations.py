from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.recommendation_service import RecommendationService
from app.schemas.recommendation import RecommendationResponse

router = APIRouter()


@router.get("", response_model=list[RecommendationResponse])
def list_recommendations(*, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate recommendations dynamically for the current user."""
    recs = RecommendationService.generate_recommendations(db, user_id=current_user.id)
    # Convert dataclass to Pydantic-compatible objects by returning as-is (from_attributes=True)
    return recs


@router.post("/generate", response_model=list[RecommendationResponse], status_code=status.HTTP_200_OK)
def generate_recommendations(*, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Force regeneration of recommendations (no persistence)."""
    recs = RecommendationService.generate_recommendations(db, user_id=current_user.id)
    return recs
