"""Paginated transaction history.

Pagination bounds are enforced here in plain Python, so the model cannot
request an unbounded dump of the history regardless of what it is asked.
"""

from __future__ import annotations

from typing import Any

from app import mock_data

DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 20


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def list_page(page_size: object = DEFAULT_PAGE_SIZE, offset: object = 0) -> dict[str, Any]:
    """Return one page of transactions, newest first, or an ERROR dict for bad input."""
    if not _is_int(page_size) or not 1 <= page_size <= MAX_PAGE_SIZE:
        return {"status": "ERROR", "reason": f"page_size must be an integer from 1 to {MAX_PAGE_SIZE}."}
    if not _is_int(offset) or offset < 0:
        return {"status": "ERROR", "reason": "offset must be an integer of 0 or more."}

    # Ids are issued sequentially, so insertion order is chronological.
    newest_first = list(reversed(mock_data.transactions.values()))
    total = len(newest_first)
    page = newest_first[offset : offset + page_size]
    next_offset = offset + page_size
    return {
        "transactions": page,
        "total": total,
        "offset": offset,
        "page_size": page_size,
        "has_more": next_offset < total,
        "next_offset": next_offset if next_offset < total else None,
    }
