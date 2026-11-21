import re
from typing import Annotated

from pydantic import AfterValidator

_DIGITS = re.compile(r"\D")
_TR_MOBILE = re.compile(r"^\+905\d{9}$")


def normalize_phone_number(value: str) -> str:
    """Normalize a Turkish mobile number to E.164 (`+905xxxxxxxxx`).

    Accepts `+90 5xx xxx xx xx`, `0090…`, `05xx…` and `5xx…`, with spaces, dashes or parentheses.
    """
    digits = _DIGITS.sub("", value)
    if digits.startswith("0090"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = "90" + digits[1:]
    elif digits.startswith("5") and len(digits) == 10:
        digits = "90" + digits

    normalized = f"+{digits}"
    if not _TR_MOBILE.match(normalized):
        raise ValueError("Enter a valid Turkish mobile number, e.g. 0555 123 45 67.")
    return normalized


PhoneNumber = Annotated[str, AfterValidator(normalize_phone_number)]
