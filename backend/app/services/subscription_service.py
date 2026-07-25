from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.statement import Subscription, SubscriptionStatus
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_detection_service import SubscriptionDetectionService


class SubscriptionService:
    @staticmethod
    def detect_subscriptions(db: Session, *, user_id: int) -> list[Subscription]:
        return SubscriptionDetectionService.detect_and_persist(db, user_id=user_id)

    @staticmethod
    def list_subscriptions(db: Session, *, user_id: int) -> list[Subscription]:
        return SubscriptionRepository.list_for_user(db, user_id=user_id)

    @staticmethod
    def review_subscription(
        db: Session, *, subscription_id: int, user_id: int, status_value: SubscriptionStatus
    ) -> Subscription:
        subscription = SubscriptionRepository.get_for_user(
            db, subscription_id=subscription_id, user_id=user_id
        )
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        return SubscriptionRepository.update_status(db, subscription=subscription, status=status_value)
