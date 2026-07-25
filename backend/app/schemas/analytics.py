from decimal import Decimal
from typing import List, Dict, Any

from pydantic import BaseModel, ConfigDict
from app.schemas.recommendation import RecommendationResponse


class Overview(BaseModel):
    score: int
    risk_level: str
    monthly_spend: Decimal
    yearly_spend: Decimal
    potential_monthly_savings: Decimal
    potential_yearly_savings: Decimal
    active_subscriptions: int
    recommendation_count: int


class CategoryItem(BaseModel):
    category: str
    amount: Decimal


class MonthlyTrendItem(BaseModel):
    year: int
    month: int
    total: Decimal


class TopSubscriptionItem(BaseModel):
    id: int
    merchant: str
    monthly: Decimal
    annual: Decimal


class BillingDistributionItem(BaseModel):
    cycle: str
    count: int


class RecentSubscriptionItem(BaseModel):
    id: int
    merchant: str
    category: str
    billing_cycle: str
    monthly_cost: Decimal
    confidence: Decimal
    status: str


class TopCostlyItem(BaseModel):
    id: int
    merchant: str
    monthly_cost: Decimal
    annual_cost: Decimal
    recommendations: List[str]


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overview: Overview
    spending_by_category: List[CategoryItem]
    monthly_trend: List[MonthlyTrendItem]
    top_subscriptions: List[TopSubscriptionItem]
    billing_distribution: List[BillingDistributionItem]
    recent_subscriptions: List[RecentSubscriptionItem]
    top_costly_subscriptions: List[TopCostlyItem]
    recommendations: List[RecommendationResponse]
