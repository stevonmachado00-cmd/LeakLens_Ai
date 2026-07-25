import csv
import io
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.schemas.transaction import ParsedTransaction


REQUIRED_COLUMNS = {"date", "merchant", "description", "amount", "currency"}
OPTIONAL_COLUMNS = {"category"}


class StatementParseError(ValueError):
    """Raised when an uploaded statement cannot be parsed into transactions."""


def parse_csv_transactions(content: bytes) -> list[ParsedTransaction]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StatementParseError("CSV files must use UTF-8 encoding.") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise StatementParseError("CSV file must include a header row.")

    columns = {column.strip().lower(): column for column in reader.fieldnames if column}
    missing_columns = REQUIRED_COLUMNS - columns.keys()
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise StatementParseError(f"CSV file is missing required columns: {missing}.")

    transactions: list[ParsedTransaction] = []
    for row_number, row in enumerate(reader, start=2):
        if not any(value and value.strip() for value in row.values()):
            continue
        transactions.append(_parse_row(row, columns, row_number))

    if not transactions:
        raise StatementParseError("CSV file does not contain any transaction rows.")

    return transactions


def _parse_row(
    row: dict[str, str | None], columns: dict[str, str], row_number: int
) -> ParsedTransaction:
    def value(column: str) -> str:
        raw_value = row.get(columns[column])
        cleaned = raw_value.strip() if raw_value else ""
        if not cleaned:
            raise StatementParseError(f"Row {row_number}: {column} is required.")
        return cleaned

    date = _parse_date(value("date"), row_number)
    merchant = value("merchant")
    description = value("description")
    amount = _parse_amount(value("amount"), row_number)
    currency = value("currency").upper()
    if len(currency) != 3 or not currency.isalpha():
        raise StatementParseError(f"Row {row_number}: currency must be a three-letter code.")

    category = None
    if "category" in columns:
        raw_category = row.get(columns["category"])
        category = raw_category.strip() if raw_category and raw_category.strip() else None

    return ParsedTransaction(
        date=date,
        merchant=merchant,
        description=description,
        amount=amount,
        currency=currency,
        category=category,
    )


def _parse_date(value: str, row_number: int) -> datetime:
    """
    Accept ISO-8601 and common bank CSV date formats.
    Examples accepted: 2026-07-25, 07/25/2026, 25/07/2026, 2026-07-25T14:30:00Z
    """
    normalized_value = value.strip().replace("Z", "+00:00")
    # Try ISO first
    try:
        parsed = datetime.fromisoformat(normalized_value)
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError:
        pass

    # Try common formats
    common_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in common_formats:
        try:
            parsed = datetime.strptime(normalized_value, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # As a last resort, try dateutil.parser if available
    try:
        from dateutil.parser import parse as _parse

        parsed = _parse(normalized_value)
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except Exception:
        raise StatementParseError(
            f"Row {row_number}: date must use ISO-8601 or a common date format (e.g. 2026-07-25 or 07/25/2026)."
        )


def _parse_amount(value: str, row_number: int) -> Decimal:
    """
    Normalize common amount representations:
    - Strip currency symbols ($, £, €)
    - Allow parentheses for negatives: (12.34) -> -12.34
    - Remove thousands separators (commas)
    - Ensure at most two decimal places
    """
    raw = value.strip()

    # Handle parentheses for negative values
    is_negative = False
    if raw.startswith("(") and raw.endswith(")"):
        is_negative = True
        raw = raw[1:-1]

    # Remove currency symbols and spaces
    # Keep digits, dot, minus and comma
    cleaned_chars = []
    for ch in raw:
        if ch.isdigit() or ch in (".", ",", "-"):
            cleaned_chars.append(ch)
    cleaned = "".join(cleaned_chars)

    # Remove thousands separator
    cleaned = cleaned.replace(",", "")

    if cleaned == "" or cleaned == "-":
        raise StatementParseError(f"Row {row_number}: amount must be a valid decimal number.")

    if is_negative and not cleaned.startswith("-"):
        cleaned = "-" + cleaned

    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise StatementParseError(f"Row {row_number}: amount must be a valid decimal number.") from exc

    if not amount.is_finite():
        raise StatementParseError(f"Row {row_number}: amount must be finite.")
    if amount.as_tuple().exponent < -2:
        raise StatementParseError(f"Row {row_number}: amount cannot have more than two decimal places.")
    return amount
