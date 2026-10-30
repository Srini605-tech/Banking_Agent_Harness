"""Deterministic transfer validation.

The LLM may request any transfer it likes; whether it actually happens is
decided entirely here, in plain Python — never by the system prompt.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app import mock_data


@dataclass
class TransferValidation:
    status: str  # "APPROVED" | "NEEDS_CLARIFICATION" | "REJECTED"
    beneficiary: dict[str, str] | None = None
    candidates: list[dict[str, str]] = field(default_factory=list)
    reason: str | None = None


MAX_QUERY_LENGTH = 100
_TRANSACTION_ID_RE = re.compile(r"TXN\d{3,}")


def validate_amount(amount: object) -> str | None:
    """Return an error message if `amount` is not a usable money value, else None.

    NaN compares False against everything, so it would slip past every
    balance/limit check; non-finite, non-numeric and sub-paisa values are
    rejected here. Positivity is checked separately in validate_transfer.
    """
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
        return "Transfer amount must be a valid number."
    if abs(amount * 100 - round(amount * 100)) > 1e-6:
        return "Transfer amount can have at most 2 decimal places."
    return None


def validate_search_query(query: object) -> str | None:
    """Return an error message if a beneficiary query is unusable, else None."""
    if not isinstance(query, str) or not query.strip():
        return "A beneficiary name, id, or last-4 digits is required."
    if len(query) > MAX_QUERY_LENGTH:
        return f"Search text must be at most {MAX_QUERY_LENGTH} characters."
    return None


def normalize_transaction_id(transaction_id: object) -> str | None:
    """Return the canonical id (e.g. 'TXN001') or None if the format is invalid."""
    if not isinstance(transaction_id, str):
        return None
    candidate = transaction_id.strip().upper()
    return candidate if _TRANSACTION_ID_RE.fullmatch(candidate) else None


def validate_transfer(beneficiary_query: str, amount: float) -> TransferValidation:
    amount_error = validate_amount(amount)
    if amount_error:
        return TransferValidation(status="REJECTED", reason=amount_error)

    query_error = validate_search_query(beneficiary_query)
    if query_error:
        return TransferValidation(status="REJECTED", reason=query_error)

    matches = mock_data.resolve_beneficiaries(beneficiary_query)

    if not matches:
        return TransferValidation(
            status="REJECTED", reason=f"No beneficiary matches '{beneficiary_query}'."
        )
    if len(matches) > 1:
        return TransferValidation(status="NEEDS_CLARIFICATION", candidates=matches)

    beneficiary = matches[0]

    if amount <= 0:
        return TransferValidation(
            status="REJECTED", reason="Transfer amount must be greater than zero."
        )

    account = mock_data.accounts[mock_data.ACCOUNT_ID]
    if account["status"] != "ACTIVE":
        return TransferValidation(status="REJECTED", reason="Your account is not active.")

    if beneficiary["status"] != "ACTIVE":
        return TransferValidation(
            status="REJECTED",
            reason=f"Beneficiary '{beneficiary['name']}' is blocked and cannot receive transfers.",
        )

    if amount > account["balance"]:
        return TransferValidation(status="REJECTED", reason="Insufficient account balance.")

    if account["daily_used"] + amount > account["daily_limit"]:
        remaining = account["daily_limit"] - account["daily_used"]
        return TransferValidation(
            status="REJECTED",
            reason=f"Daily transfer limit exceeded. Only {remaining} remains today.",
        )

    return TransferValidation(status="APPROVED", beneficiary=beneficiary)
