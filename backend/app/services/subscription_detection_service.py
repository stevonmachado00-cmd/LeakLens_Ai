from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean

from sqlalchemy.orm import Session

from app.models.statement import BillingCycle, Subscription, Transaction
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.merchant_normalization_service import normalize_merchant


@dataclass(frozen=True)
class DetectedSubscription:
    merchant: str
    normalized_merchant: str
    billing_cycle: BillingCycle
    average_amount: Decimal
    last_charge_date: datetime
    confidence: Decimal


_CYCLE_WINDOWS = {
    BillingCycle.WEEKLY: (7, 2),
    BillingCycle.MONTHLY: (30, 7),
    BillingCycle.QUARTERLY: (91, 15),
    BillingCycle.YEARLY: (365, 45),
}
_MONEY_QUANTUM = Decimal("0.01")
_CONFIDENCE_QUANTUM = Decimal("0.001")


class SubscriptionDetectionService:
    @staticmethod
    def detect_and_persist(db: Session, *, user_id: int) -> list[Subscription]:
        transactions = TransactionRepository.list_for_user(db, user_id=user_id)
        candidates = SubscriptionDetectionService.detect(transactions)
        return [
            SubscriptionRepository.upsert_detection(
                db,
                user_id=user_id,
                merchant=candidate.merchant,
                normalized_merchant=candidate.normalized_merchant,
                billing_cycle=candidate.billing_cycle,
                average_amount=candidate.average_amount,
                last_charge_date=candidate.last_charge_date,
                confidence=candidate.confidence,
            )
            for candidate in candidates
        ]

    @staticmethod
    def detect(transactions: list[Transaction]) -> list[DetectedSubscription]:
        groups: dict[tuple[str, str], list[Transaction]] = defaultdict(list)
        for transaction in transactions:
            normalized = normalize_merchant(transaction.merchant, transaction.description)
            if normalized and transaction.amount != 0:
                groups[(normalized, transaction.currency)].append(transaction)

        candidates: list[DetectedSubscription] = []
        for (normalized, _currency), group in groups.items():
            candidate = _detect_group(normalized, group)
            if candidate:
                candidates.append(candidate)
        return candidates


def _detect_group(normalized_merchant: str, transactions: list[Transaction]) -> DetectedSubscription | None:
    if len(transactions) < 3:
        return None

    ordered = sorted(transactions, key=lambda transaction: transaction.date)
    intervals = [
        max(0, (current.date - previous.date).total_seconds() / 86400)
        for previous, current in zip(ordered, ordered[1:])
    ]
    average_interval = mean(intervals)
    cycle, tolerance = min(
        _CYCLE_WINDOWS.items(), key=lambda item: abs(average_interval - item[1][0])
    )
    target_days, tolerance_days = tolerance
    if any(abs(interval - target_days) > tolerance_days for interval in intervals):
        return None

    amounts = [abs(Decimal(transaction.amount)) for transaction in ordered]
    average_amount = sum(amounts) / len(amounts)
    amount_tolerance = max(Decimal("1.00"), average_amount * Decimal("0.10"))
    max_amount_deviation = max(abs(amount - average_amount) for amount in amounts)
    if max_amount_deviation > amount_tolerance:
        return None

    interval_deviation = mean(abs(interval - target_days) for interval in intervals)
    regularity = max(0.0, 1 - interval_deviation / tolerance_days)
    stability = max(0.0, 1 - float(max_amount_deviation / amount_tolerance))
    history = min(len(ordered) / 6, 1.0)
    confidence = Decimal(str(0.50 * regularity + 0.35 * stability + 0.15 * history))
    if confidence < Decimal("0.700"):
        return None

    merchant = max(ordered, key=lambda transaction: len(transaction.merchant)).merchant
    return DetectedSubscription(
        merchant=merchant,
        normalized_merchant=normalized_merchant,
        billing_cycle=cycle,
        average_amount=average_amount.quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP),
        last_charge_date=ordered[-1].date,
        confidence=confidence.quantize(_CONFIDENCE_QUANTUM, rounding=ROUND_HALF_UP),
    )
