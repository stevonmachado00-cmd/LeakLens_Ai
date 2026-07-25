from typing import Optional

from sqlalchemy.orm import Session

from app.models.statement import BillingCycle, Subscription, SubscriptionStatus


class SubscriptionRepository:
    @staticmethod
    def list_for_user(db: Session, *, user_id: int) -> list[Subscription]:
        return (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .order_by(Subscription.last_charge_date.desc())
            .all()
        )

    @staticmethod
    def get_for_user(db: Session, *, subscription_id: int, user_id: int) -> Optional[Subscription]:
        return (
            db.query(Subscription)
            .filter(Subscription.id == subscription_id, Subscription.user_id == user_id)
            .first()
        )

    @staticmethod
    def upsert_detection(
        db: Session,
        *,
        user_id: int,
        merchant: str,
        normalized_merchant: str,
        billing_cycle: BillingCycle,
        average_amount,
        last_charge_date,
        confidence,
    ) -> Subscription:
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.normalized_merchant == normalized_merchant,
                Subscription.billing_cycle == billing_cycle,
            )
            .first()
        )
        if subscription:
            subscription.merchant = merchant
            subscription.average_amount = average_amount
            subscription.last_charge_date = last_charge_date
            subscription.confidence = confidence
        else:
            subscription = Subscription(
                user_id=user_id,
                merchant=merchant,
                normalized_merchant=normalized_merchant,
                billing_cycle=billing_cycle,
                average_amount=average_amount,
                last_charge_date=last_charge_date,
                confidence=confidence,
                status=SubscriptionStatus.DETECTED,
            )
            db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def update_status(
        db: Session, *, subscription: Subscription, status: SubscriptionStatus
    ) -> Subscription:
        subscription.status = status
        db.commit()
        db.refresh(subscription)
        return subscription
