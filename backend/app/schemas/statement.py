from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.statement import StatementStatus


class StatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: StatementStatus
    uploaded_at: datetime
    updated_at: datetime


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime
    merchant: str
    description: str
    amount: Decimal
    currency: str
    category: Optional[str]
    created_at: datetime
