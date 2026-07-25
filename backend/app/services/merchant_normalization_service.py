import re


_NOISE_TOKENS = {
    "ach",
    "card",
    "credit",
    "debit",
    "online",
    "payment",
    "pos",
    "purchase",
    "recurring",
    "transaction",
}
_DOMAIN_SUFFIXES = {"com", "in", "io", "net", "org"}


def normalize_merchant(merchant: str, description: str = "") -> str:
    """Create a conservative grouping key without relying on an external model."""
    source = merchant.strip() or description.strip()
    source = source.casefold()
    source = re.split(r"[*#]", source, maxsplit=1)[0]
    tokens = re.findall(r"[a-z]+", source)
    tokens = [token for token in tokens if token not in _NOISE_TOKENS]
    while tokens and tokens[-1] in _DOMAIN_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)
