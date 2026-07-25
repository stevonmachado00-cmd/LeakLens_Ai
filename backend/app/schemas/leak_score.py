from decimal import Decimal
from typing import List, Dict

from pydantic import BaseModel, ConfigDict


class BreakdownItem(BaseModel):
    factor: str
    impact: Decimal


class LeakScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    breakdown: List[BreakdownItem]
