from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ParsedTransaction:
    """Normalized transaction data produced by a statement parser."""

    date: datetime
    merchant: str
    description: str
    amount: Decimal
    currency: str
    category: str | None
