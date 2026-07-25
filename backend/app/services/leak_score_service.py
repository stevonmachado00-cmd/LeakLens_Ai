from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict

from sqlalchemy.orm import Session

from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.recommendation_service import RecommendationService, Recommendation

# Scoring constants (tunable)
BASE_SCORE = 100
# Active subscriptions deductions
SUBSCRIPTION_COUNT_THRESHOLDS = [(2, 0), (5, 5), (9, 10), (9999, 20)]  # (max_count, deduction)
# Monthly spend thresholds (USD)
MONTHLY_SPEND_THRESHOLDS = [(20, 0), (100, 5), (300, 15), (999999, 30)]  # (max_amt, deduction)
# Duplicate subscription penalty per extra subscription (cap applied)
DUPLICATE_PENALTY_PER = Decimal("3.0")
DUPLICATE_PENALTY_CAP = Decimal("15.0")
# High-cost subscription penalty per subscription
HIGH_COST_PENALTY_PER = Decimal("5.0")
HIGH_COST_PENALTY_CAP = Decimal("25.0")
# Long-running subscription penalty per subscription
LONG_RUNNING_PENALTY_PER = Decimal("2.0")
LONG_RUNNING_PENALTY_CAP = Decimal("10.0")
# Category overlap penalty per overlapping category group
CATEGORY_OVERLAP_PENALTY_PER = Decimal("5.0")
CATEGORY_OVERLAP_PENALTY_CAP = Decimal("15.0")
# Potential savings scaling - max deduction from savings
SAVINGS_DEDUCTION_MAX = Decimal("30.0")
# Recommendation count bonus
NO_RECOMMENDATION_BONUS = Decimal("2.0")
# Confidence-based adjustments
CONFIDENCE_LOW_THRESHOLD = Decimal("0.5")
CONFIDENCE_LOW_PENALTY = Decimal("5.0")
CONFIDENCE_HIGH_THRESHOLD = Decimal("0.85")
CONFIDENCE_HIGH_BONUS = Decimal("2.0")


@dataclass
class LeakScoreResult:
    score: int
    risk_level: str
    monthly_spend: Decimal
    yearly_spend: Decimal
    potential_monthly_savings: Decimal
    potential_yearly_savings: Decimal
    active_subscriptions: int
    duplicate_subscriptions: int
    high_cost_subscriptions: int
    recommendation_count: int
    summary: str
    breakdown: List[Dict[str, Decimal]]


class LeakScoreService:
    @staticmethod
    def calculate_score(db: Session, *, user_id: int) -> LeakScoreResult:
        # Load subscriptions and transactions
        subs = SubscriptionRepository.list_for_user(db, user_id=user_id)
        txs = TransactionRepository.list_for_user(db, user_id=user_id)

        # Generate recommendations (in-memory) and reuse detectors
        recs: List[Recommendation] = RecommendationService.generate_recommendations(db, user_id=user_id)

        # Compute basic stats
        active_subs = [s for s in subs if getattr(s, "status", None) != None]
        active_count = len(active_subs)

        monthly_spend = Decimal("0.00")
        for s in active_subs:
            try:
                amt = Decimal(s.average_amount)
            except Exception:
                amt = Decimal("0.00")
            # billing cycle conversion: reuse helper from recommendation service if available
            from app.services.recommendation_service import _to_monthly

            monthly_spend += _to_monthly(amt, s.billing_cycle)

        yearly_spend = (monthly_spend * Decimal("12")).quantize(Decimal("0.01"))

        # Aggregate potential savings from recommendations
        potential_monthly_savings = sum((r.estimated_monthly_savings for r in recs), Decimal("0.00"))
        potential_yearly_savings = sum((r.estimated_yearly_savings for r in recs), Decimal("0.00"))

        # Count duplicates, high-cost, category overlap via recommendation types
        duplicate_count = 0
        high_cost_count = 0
        category_overlap_groups = 0
        long_running_count = 0
        for r in recs:
            if r.recommendation_type == "duplicate":
                # related_subscription_ids contains all subs in the duplicate group
                # count extras beyond one per group
                duplicate_count += max(0, len(r.related_subscription_ids) - 1)
            elif r.recommendation_type == "high_cost":
                high_cost_count += 1
            elif r.recommendation_type == "category_overlap":
                category_overlap_groups += 1
            elif r.recommendation_type == "long_running":
                long_running_count += 1

        recommendation_count = len(recs)

        # Start scoring
        deductions = Decimal("0.0")
        breakdown = []

        # Subscriptions count deduction
        sub_deduction = Decimal("0.0")
        for max_count, ded in SUBSCRIPTION_COUNT_THRESHOLDS:
            if active_count <= max_count:
                sub_deduction = Decimal(str(ded))
                break
        deductions += sub_deduction
        breakdown.append({"factor": "active_subscriptions", "impact": sub_deduction})

        # Monthly spend deduction
        spend_deduction = Decimal("0.0")
        for max_amt, ded in MONTHLY_SPEND_THRESHOLDS:
            if monthly_spend <= Decimal(str(max_amt)):
                spend_deduction = Decimal(str(ded))
                break
        deductions += spend_deduction
        breakdown.append({"factor": "monthly_spend", "impact": spend_deduction})

        # Duplicate penalty
        dup_penalty = min(DUPLICATE_PENALTY_PER * Decimal(duplicate_count), DUPLICATE_PENALTY_CAP)
        deductions += dup_penalty
        breakdown.append({"factor": "duplicate_subscriptions", "impact": dup_penalty})

        # High-cost penalty
        high_cost_penalty = min(HIGH_COST_PENALTY_PER * Decimal(high_cost_count), HIGH_COST_PENALTY_CAP)
        deductions += high_cost_penalty
        breakdown.append({"factor": "high_cost_subscriptions", "impact": high_cost_penalty})

        # Long-running penalty
        long_running_penalty = min(LONG_RUNNING_PENALTY_PER * Decimal(long_running_count), LONG_RUNNING_PENALTY_CAP)
        deductions += long_running_penalty
        breakdown.append({"factor": "long_running_subscriptions", "impact": long_running_penalty})

        # Category overlap penalty
        cat_penalty = min(CATEGORY_OVERLAP_PENALTY_PER * Decimal(category_overlap_groups), CATEGORY_OVERLAP_PENALTY_CAP)
        deductions += cat_penalty
        breakdown.append({"factor": "category_overlap", "impact": cat_penalty})

        # Potential savings deduction (scale by relative to spend)
        savings_ratio = Decimal("0.0")
        if monthly_spend > Decimal("0.0"):
            savings_ratio = (potential_monthly_savings / monthly_spend)
        savings_deduction = min((savings_ratio * SAVINGS_DEDUCTION_MAX).quantize(Decimal("0.01")), SAVINGS_DEDUCTION_MAX)
        deductions += savings_deduction
        breakdown.append({"factor": "potential_savings", "impact": savings_deduction})

        # Recommendation count bonus/penalty
        rec_bonus = Decimal("0.0")
        if recommendation_count == 0:
            rec_bonus = -NO_RECOMMENDATION_BONUS * Decimal("-1")  # add to score by subtracting negative
            # to keep uniformity, store as negative impact means improvement
            # Represent bonus as negative impact (reducing deductions)
            deductions -= NO_RECOMMENDATION_BONUS
            breakdown.append({"factor": "no_recommendations_bonus", "impact": -NO_RECOMMENDATION_BONUS})
        else:
            breakdown.append({"factor": "recommendation_count", "impact": Decimal(str(recommendation_count))})

        # Confidence adjustments
        avg_conf = Decimal("0.0")
        if active_count > 0:
            confs = [Decimal(getattr(s, "confidence", 0) or 0) for s in active_subs]
            avg_conf = sum(confs) / Decimal(len(confs))
            if avg_conf < CONFIDENCE_LOW_THRESHOLD:
                deductions += CONFIDENCE_LOW_PENALTY
                breakdown.append({"factor": "low_confidence", "impact": CONFIDENCE_LOW_PENALTY})
            elif avg_conf > CONFIDENCE_HIGH_THRESHOLD:
                # treat as bonus (reduce deductions)
                deductions -= CONFIDENCE_HIGH_BONUS
                breakdown.append({"factor": "high_confidence_bonus", "impact": -CONFIDENCE_HIGH_BONUS})
        else:
            breakdown.append({"factor": "average_confidence", "impact": avg_conf})

        # Final score
        raw_score = Decimal(str(BASE_SCORE)) - deductions
        if raw_score < Decimal("0"):
            raw_score = Decimal("0")
        if raw_score > Decimal("100"):
            raw_score = Decimal("100")

        score_int = int(raw_score.quantize(Decimal("1")))

        # Risk level classification
        if score_int >= 80:
            risk = "Excellent"
        elif score_int >= 60:
            risk = "Good"
        elif score_int >= 40:
            risk = "Medium"
        elif score_int >= 20:
            risk = "High"
        else:
            risk = "Critical"

        summary = (
            f"Your Leak Score is {score_int}. Monthly recurring spend is ${monthly_spend:.2f}. "
            f"Potential monthly savings identified: ${potential_monthly_savings:.2f}."
        )

        return LeakScoreResult(
            score=score_int,
            risk_level=risk,
            monthly_spend=monthly_spend.quantize(Decimal("0.01")),
            yearly_spend=yearly_spend,
            potential_monthly_savings=potential_monthly_savings.quantize(Decimal("0.01")),
            potential_yearly_savings=potential_yearly_savings.quantize(Decimal("0.01")),
            active_subscriptions=active_count,
            duplicate_subscriptions=duplicate_count,
            high_cost_subscriptions=high_cost_count,
            recommendation_count=recommendation_count,
            summary=summary,
            breakdown=breakdown,
        )
