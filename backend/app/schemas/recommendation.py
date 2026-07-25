from decimal import Decimal
from typing import List

from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    recommendation_type: str
    severity: str
    estimated_monthly_savings: Decimal
    estimated_yearly_savings: Decimal
    confidence: Decimal
    related_subscription_ids: List[int]
    related_subscription_names: List[str]
