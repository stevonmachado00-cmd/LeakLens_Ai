from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.recommendation_service import RecommendationService
from app.services.leak_score_service import LeakScoreService


@dataclass
class AnalyticsResult:
    overview: Dict[str, Any]
    spending_by_category: List[Dict[str, Any]]
    monthly_trend: List[Dict[str, Any]]
    top_subscriptions: List[Dict[str, Any]]
    billing_distribution: List[Dict[str, Any]]
    recent_subscriptions: List[Dict[str, Any]]
    top_costly_subscriptions: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]


def _to_monthly(avg_amount: Decimal, cycle) -> Decimal:
    # reuse same conversion logic as recommendation service helper
    from app.services.recommendation_service import _to_monthly as _r_to_monthly

    return _r_to_monthly(avg_amount, cycle)


class AnalyticsService:
    @staticmethod
    def dashboard(db: Session, *, user_id: int) -> AnalyticsResult:
        # Load data
        subs = SubscriptionRepository.list_for_user(db, user_id=user_id)
        txs = TransactionRepository.list_for_user(db, user_id=user_id)

        # Reuse recommendations and leak score
        recs = RecommendationService.generate_recommendations(db, user_id=user_id)
        leak = LeakScoreService.calculate_score(db, user_id=user_id)

        # Overview: reuse leak result fields and add recommendations count
        overview = {
            "score": leak.score,
            "risk_level": leak.risk_level,
            "monthly_spend": leak.monthly_spend,
            "yearly_spend": leak.yearly_spend,
            "potential_monthly_savings": leak.potential_monthly_savings,
            "potential_yearly_savings": leak.potential_yearly_savings,
            "active_subscriptions": leak.active_subscriptions,
            "recommendation_count": leak.recommendation_count,
        }


        # Spending by category (raw sums)
        cat_totals: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for t in txs:
            cat = getattr(t, "category", None) or "Uncategorized"
            try:
                amt = Decimal(t.amount)
            except Exception:
                amt = Decimal("0.00")
            cat_totals[cat] += amt

        spending_by_category = [
            {"category": k, "amount": v.quantize(Decimal("0.01"))} for k, v in cat_totals.items()
        ]

        # Monthly trend - last 12 months raw totals
        now = datetime.now(timezone.utc)
        monthly = defaultdict(Decimal)
        for t in txs:
            tx_date = t.date
            if tx_date.tzinfo is None:
                tx_date = tx_date.replace(tzinfo=timezone.utc)
            ym = (tx_date.year, tx_date.month)
            try:
                monthly[ym] += Decimal(t.amount)
            except Exception:
                pass

        # Build last 12 months list
        monthly_trend = []
        for i in range(11, -1, -1):
            # get year-month i months ago
            from dateutil.relativedelta import relativedelta

            dt = now - relativedelta(months=i)
            key = (dt.year, dt.month)
            total = monthly.get(key, Decimal("0.00"))
            monthly_trend.append({"year": dt.year, "month": dt.month, "total": total.quantize(Decimal("0.01"))})

        # Top recurring subscriptions by monthly cost (top 10)
        subs_with_monthly = []
        for s in subs:
            try:
                monthly_amt = _to_monthly(Decimal(s.average_amount), s.billing_cycle)
            except Exception:
                monthly_amt = Decimal("0.00")
            subs_with_monthly.append((s, monthly_amt))

        subs_with_monthly.sort(key=lambda x: x[1], reverse=True)
        top_subscriptions = []
        for s, monthly_amt in subs_with_monthly[:10]:
            top_subscriptions.append(
                {
                    "id": s.id,
                    "merchant": s.merchant,
                    "monthly": monthly_amt.quantize(Decimal("0.01")),
                    "annual": (monthly_amt * Decimal("12")).quantize(Decimal("0.01")),
                }
            )

        # Billing cycle distribution
        cycle_counts: Dict[str, int] = defaultdict(int)
        for s in subs:
            cyc = getattr(s, "billing_cycle", None)
            cycle_counts[str(cyc)] += 1
        billing_distribution = [{"cycle": k, "count": v} for k, v in cycle_counts.items()]

        # Recent subscriptions (most recently created or last_charge_date)
        recent = sorted(subs, key=lambda s: getattr(s, "last_charge_date", None) or datetime.min, reverse=True)
        recent_subscriptions = []
        for s in recent[:10]:
            try:
                monthly_amt = _to_monthly(Decimal(s.average_amount), s.billing_cycle)
            except Exception:
                monthly_amt = Decimal("0.00")
            recent_subscriptions.append(
                {
                    "id": s.id,
                    "merchant": s.merchant,
                    "category": getattr(s, "category", None) or "",
                    "billing_cycle": str(s.billing_cycle),
                    "monthly_cost": monthly_amt.quantize(Decimal("0.01")),
                    "confidence": getattr(s, "confidence", Decimal("0.0")),
                    "status": str(getattr(s, "status", None)),
                }
            )

        # Top costly subscriptions table (top 10 by monthly) with associated recommendation text if present
        # Map subscription id -> recommendation descriptions
        rec_map: Dict[int, List[str]] = defaultdict(list)
        for r in recs:
            for sid in getattr(r, "related_subscription_ids", []):
                rec_map[sid].append(r.description)

        top_costly_subscriptions = []
        for s, monthly_amt in subs_with_monthly[:10]:
            top_costly_subscriptions.append(
                {
                    "id": s.id,
                    "merchant": s.merchant,
                    "monthly_cost": monthly_amt.quantize(Decimal("0.01")),
                    "annual_cost": (monthly_amt * Decimal("12")).quantize(Decimal("0.01")),
                    "recommendations": rec_map.get(s.id, []),
                }
            )

        # Prepare recommendations serialized
        rec_list = []
        for r in recs:
            rec_list.append(
                {
                    "title": r.title,
                    "description": r.description,
                    "recommendation_type": r.recommendation_type,
                    "severity": r.severity,
                    "estimated_monthly_savings": r.estimated_monthly_savings,
                    "estimated_yearly_savings": r.estimated_yearly_savings,
                    "confidence": r.confidence,
                    "related_subscription_ids": r.related_subscription_ids,
                    "related_subscription_names": r.related_subscription_names,
                }
            )

        return AnalyticsResult(
            overview=overview,
            spending_by_category=spending_by_category,
            monthly_trend=monthly_trend,
            top_subscriptions=top_subscriptions,
            billing_distribution=billing_distribution,
            recent_subscriptions=recent_subscriptions,
            top_costly_subscriptions=top_costly_subscriptions,
            recommendations=rec_list,
        )
