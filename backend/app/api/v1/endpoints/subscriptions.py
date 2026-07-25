from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.subscription import SubscriptionResponse, SubscriptionReviewUpdate
from app.services.subscription_service import SubscriptionService


router = APIRouter()


@router.post("/detect", response_model=list[SubscriptionResponse])
def detect_subscriptions(
    *, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[SubscriptionResponse]:
    return SubscriptionService.detect_subscriptions(db, user_id=current_user.id)


@router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(
    *, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[SubscriptionResponse]:
    return SubscriptionService.list_subscriptions(db, user_id=current_user.id)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def review_subscription(
    *,
    subscription_id: int,
    request: SubscriptionReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    return SubscriptionService.review_subscription(
        db, subscription_id=subscription_id, user_id=current_user.id, status_value=request.status
    )
