from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from statistics import median
from typing import Iterable, List, Tuple

from sqlalchemy.orm import Session

from app.models.statement import Subscription, BillingCycle, Transaction
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.merchant_normalization_service import normalize_merchant


@dataclass
class Recommendation:
    title: str
    description: str
    recommendation_type: str
    severity: str  # low, medium, high
    estimated_monthly_savings: Decimal
    estimated_yearly_savings: Decimal
    confidence: Decimal
    related_subscription_ids: List[int]
    related_subscription_names: List[str]


def _to_monthly(avg_amount: Decimal, cycle: BillingCycle) -> Decimal:
    if avg_amount is None:
        return Decimal("0.00")
    if cycle == BillingCycle.WEEKLY:
        return (avg_amount * Decimal("52")) / Decimal("12")
    if cycle == BillingCycle.MONTHLY:
        return avg_amount
    if cycle == BillingCycle.QUARTERLY:
        return (avg_amount * Decimal("4")) / Decimal("12")
    if cycle == BillingCycle.YEARLY:
        return avg_amount / Decimal("12")
    return avg_amount


class RecommendationService:
    @staticmethod
    def generate_recommendations(db: Session, *, user_id: int) -> List[Recommendation]:
        subscriptions = SubscriptionRepository.list_for_user(db, user_id=user_id)
        transactions = TransactionRepository.list_for_user(db, user_id=user_id)

        # Build transaction groups keyed by normalized merchant
        tx_by_normalized: dict[str, List[Transaction]] = defaultdict(list)
        for tx in transactions:
            key = normalize_merchant(tx.merchant, tx.description)
            tx_by_normalized[key].append(tx)

        # Precompute monthly amounts
        sub_monthly: dict[int, Decimal] = {}
        for sub in subscriptions:
            sub_monthly[sub.id] = _to_monthly(Decimal(sub.average_amount), sub.billing_cycle)

        recommendations: List[Recommendation] = []

        # Run detectors
        recommendations.extend(_detect_duplicates(subscriptions, sub_monthly))
        recommendations.extend(_detect_long_running(subscriptions, tx_by_normalized))
        recommendations.extend(_detect_high_cost(subscriptions, sub_monthly))
        recommendations.extend(_detect_category_overlap(subscriptions, tx_by_normalized))
        recommendations.extend(_detect_annual_savings(subscriptions, sub_monthly))
        recommendations.extend(_detect_spending_growth(transactions))
        recommendations.extend(_detect_unused_subscription(subscriptions))

        return recommendations


# Detector implementations

def _detect_duplicates(subscriptions: Iterable[Subscription], sub_monthly: dict[int, Decimal]) -> List[Recommendation]:
    by_norm = defaultdict(list)
    for sub in subscriptions:
        by_norm[sub.normalized_merchant].append(sub)

    recs: List[Recommendation] = []
    for norm, group in by_norm.items():
        if len(group) < 2:
            continue
        # compute estimated saving as sum of all but largest monthly amount
        monthlys = sorted([(sub.id, sub_monthly.get(sub.id, Decimal(0))) for sub in group], key=lambda x: x[1], reverse=True)
        if len(monthlys) < 2:
            continue
        largest = monthlys[0][1]
        others_sum = sum(m for _id, m in monthlys[1:])
        est_monthly = others_sum
        est_yearly = est_monthly * Decimal("12")
        confidence = min(Decimal(getattr(group[0], "confidence", 0) or 0), *(Decimal(getattr(s, "confidence", 0) or 0) for s in group))
        confidence = (confidence + Decimal("0.7")) / Decimal("2.0")
        recs.append(
            Recommendation(
                title="You may have duplicate subscriptions",
                description=(f"Found {len(group)} subscriptions that look like the same service ({norm})."
                             " Consider consolidating or cancelling duplicates."),
                recommendation_type="duplicate",
                severity="medium",
                estimated_monthly_savings=est_monthly.quantize(Decimal("0.01")),
                estimated_yearly_savings=est_yearly.quantize(Decimal("0.01")),
                confidence=confidence.quantize(Decimal("0.001")),
                related_subscription_ids=[s.id for s in group],
                related_subscription_names=[s.merchant for s in group],
            )
        )
    return recs


def _detect_long_running(subscriptions: Iterable[Subscription], tx_by_normalized: dict[str, List[Transaction]]) -> List[Recommendation]:
    recs: List[Recommendation] = []
    now = datetime.now(timezone.utc)
    for sub in subscriptions:
        # Use created_at when available or infer from transactions
        created_at = getattr(sub, "created_at", None)
        if not created_at:
            # Try from transactions
            txs = tx_by_normalized.get(sub.normalized_merchant, [])
            if txs:
                created_at = min(t.date for t in txs)
        if not created_at:
            continue
        # Normalize naive datetimes to UTC
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (now - created_at).days
        if age_days >= 365:
            est_monthly = _to_monthly(Decimal(sub.average_amount), sub.billing_cycle)
            recs.append(
                Recommendation(
                    title="Long-running subscription",
                    description=(f"{sub.merchant} has been active for over {age_days // 30} months."),
                    recommendation_type="long_running",
                    severity="medium",
                    estimated_monthly_savings=Decimal("0.00"),
                    estimated_yearly_savings=Decimal("0.00"),
                    confidence=Decimal("0.80"),
                    related_subscription_ids=[sub.id],
                    related_subscription_names=[sub.merchant],
                )
            )
    return recs


def _detect_high_cost(subscriptions: Iterable[Subscription], sub_monthly: dict[int, Decimal]) -> List[Recommendation]:
    # Group by billing cycle
    groups = defaultdict(list)
    for sub in subscriptions:
        groups[sub.billing_cycle].append(sub)

    recs: List[Recommendation] = []
    for cycle, subs in groups.items():
        amounts = [sub_monthly.get(s.id, Decimal(0)) for s in subs]
        if len(amounts) < 2:
            continue
        try:
            med = median([float(a) for a in amounts])
            med = Decimal(str(med))
        except Exception:
            continue
        for s in subs:
            amt = sub_monthly.get(s.id, Decimal(0))
            if med > 0 and amt > med * Decimal("1.5"):
                est_monthly = amt - med
                recs.append(
                    Recommendation(
                        title="Subscription appears expensive compared to peers",
                        description=(f"{s.merchant} costs {amt:.2f} per month compared to a median of {med:.2f} for similar subscriptions."),
                        recommendation_type="high_cost",
                        severity="medium",
                        estimated_monthly_savings=est_monthly.quantize(Decimal("0.01")),
                        estimated_yearly_savings=(est_monthly * Decimal("12")).quantize(Decimal("0.01")),
                        confidence=min(Decimal(getattr(s, "confidence", 0) or 0) + Decimal("0.2"), Decimal("0.99")),
                        related_subscription_ids=[s.id],
                        related_subscription_names=[s.merchant],
                    )
                )
    return recs


def _detect_category_overlap(subscriptions: Iterable[Subscription], tx_by_normalized: dict[str, List[Transaction]]) -> List[Recommendation]:
    # Map each subscription to its predominant transaction category (if available)
    cat_map = defaultdict(list)  # category -> list of subs
    for sub in subscriptions:
        txs = tx_by_normalized.get(sub.normalized_merchant, [])
        cats = [t.category for t in txs if getattr(t, "category", None)]
        if not cats:
            continue
        # choose most common category
        cat_counts = defaultdict(int)
        for c in cats:
            cat_counts[c] += 1
        predominant = max(cat_counts.items(), key=lambda x: x[1])[0]
        cat_map[predominant].append(sub)

    recs: List[Recommendation] = []
    for cat, subs in cat_map.items():
        if len(subs) < 2:
            continue
        est_monthly = sum((_to_monthly(Decimal(s.average_amount), s.billing_cycle) for s in subs), Decimal("0.00")) * Decimal("0.2")
        recs.append(
            Recommendation(
                title="Multiple subscriptions in the same category",
                description=(f"You have {len(subs)} subscriptions classified as {cat}. Consider consolidating."),
                recommendation_type="category_overlap",
                severity="low",
                estimated_monthly_savings=est_monthly.quantize(Decimal("0.01")),
                estimated_yearly_savings=(est_monthly * Decimal("12")).quantize(Decimal("0.01")),
                confidence=Decimal("0.6"),
                related_subscription_ids=[s.id for s in subs],
                related_subscription_names=[s.merchant for s in subs],
            )
        )
    return recs


def _detect_annual_savings(subscriptions: Iterable[Subscription], sub_monthly: dict[int, Decimal]) -> List[Recommendation]:
    recs: List[Recommendation] = []
    for s in subscriptions:
        if s.billing_cycle == BillingCycle.MONTHLY:
            monthly = sub_monthly.get(s.id, Decimal(0))
            if monthly <= 0:
                continue
            # assume a modest 10% annual discount
            est_yearly = (monthly * Decimal("12")) * Decimal("0.10")
            est_monthly = (est_yearly / Decimal("12"))
            recs.append(
                Recommendation(
                    title="Annual billing could reduce your total cost",
                    description=(f"Paying annually for {s.merchant} may save approximately {est_yearly:.2f} per year."),
                    recommendation_type="annual_savings",
                    severity="low",
                    estimated_monthly_savings=est_monthly.quantize(Decimal("0.01")),
                    estimated_yearly_savings=est_yearly.quantize(Decimal("0.01")),
                    confidence=Decimal("0.5"),
                    related_subscription_ids=[s.id],
                    related_subscription_names=[s.merchant],
                )
            )
    return recs


def _detect_spending_growth(transactions: List[Transaction]) -> List[Recommendation]:
    recs: List[Recommendation] = []
    if not transactions:
        return recs
    # Build monthly totals for the last 12 months
    now = datetime.now(timezone.utc)
    monthly = defaultdict(Decimal)
    for t in transactions:
        tx_date = t.date
        if tx_date.tzinfo is None:
            tx_date = tx_date.replace(tzinfo=timezone.utc)
        ym = (tx_date.year, tx_date.month)
        monthly[ym] += Decimal(t.amount)

    # sort months
    months = sorted(monthly.items(), key=lambda x: x[0])
    if len(months) < 6:
        return recs
    # Compare average of last 3 months vs previous 3 months
    last3 = [amt for (ym, amt) in months[-3:]]
    prev3 = [amt for (ym, amt) in months[-6:-3]]
    if not prev3 or not last3:
        return recs
    avg_last = sum(last3) / len(last3)
    avg_prev = sum(prev3) / len(prev3)
    if avg_prev <= 0:
        return recs
    growth = (avg_last - avg_prev) / abs(avg_prev)
    if growth > 0.25:
        est_monthly = (avg_last - avg_prev)
        recs.append(
            Recommendation(
                title="Your recurring spending has increased significantly",
                description=("Recent months show an increase in recurring charges compared to prior months."),
                recommendation_type="spending_growth",
                severity="medium",
                estimated_monthly_savings=est_monthly.quantize(Decimal("0.01")),
                estimated_yearly_savings=(est_monthly * Decimal("12")).quantize(Decimal("0.01")),
                confidence=Decimal("0.7"),
                related_subscription_ids=[],
                related_subscription_names=[],
            )
        )
    return recs


def _detect_unused_subscription(subscriptions: Iterable[Subscription]) -> List[Recommendation]:
    recs: List[Recommendation] = []
    now = datetime.now(timezone.utc)
    for s in subscriptions:
        last = getattr(s, "last_charge_date", None)
        if last is None:
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if (now - last).days > 180:
            est_monthly = _to_monthly(Decimal(s.average_amount), s.billing_cycle)
            recs.append(
                Recommendation(
                    title="Consider cancelling this low-activity subscription",
                    description=(f"{s.merchant} has not been charged in over {(now-last).days} days."),
                    recommendation_type="unused",
                    severity="low",
                    estimated_monthly_savings=est_monthly.quantize(Decimal("0.01")),
                    estimated_yearly_savings=(est_monthly * Decimal("12")).quantize(Decimal("0.01")),
                    confidence=Decimal("0.6"),
                    related_subscription_ids=[s.id],
                    related_subscription_names=[s.merchant],
                )
            )
    return recs
