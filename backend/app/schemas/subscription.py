from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.statement import BillingCycle, SubscriptionStatus


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant: str
    normalized_merchant: str
    billing_cycle: BillingCycle
    average_amount: Decimal
    last_charge_date: datetime
    confidence: Decimal
    status: SubscriptionStatus
    created_at: datetime
    updated_at: datetime


class SubscriptionReviewUpdate(BaseModel):
    status: SubscriptionStatus
