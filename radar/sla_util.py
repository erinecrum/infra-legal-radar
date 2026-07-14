"""Shared SLA helpers used by both the SLA source (extraction) and the
translation layer (deadline computation).

The claim-window rule AWS uses for the SLAs we track is: a credit request must
be received "by the end of the second billing cycle after which the incident
occurred." A billing cycle is a calendar month. So for an incident in month M,
the deadline is the last day of month M+2.

We surface this as an ESTIMATE. Billing-cycle boundaries can differ from
calendar months for some accounts/arrangements, so the memo always instructs
the attorney to confirm against the actual SLA text and invoice dates rather
than treating the computed date as authoritative.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Optional

_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}


def parse_billing_cycle_ordinal(text: str) -> Optional[int]:
    """Extract N from '...end of the <N-th> billing cycle...' as an int, or None."""
    import re

    m = re.search(r"end of the (\w+) billing cycle", text, re.IGNORECASE)
    if not m:
        return None
    return _ORDINALS.get(m.group(1).lower())


def _to_date(value) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # Accept ISO strings, with or without a trailing 'Z' or timezone.
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
    return None


def end_of_month(d: date) -> date:
    last = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


def compute_claim_deadline(incident_date, months_after: int = 2) -> Optional[date]:
    """Estimated credit-claim deadline: end of the month `months_after` months
    after the incident month. Returns None if the date can't be parsed."""
    d = _to_date(incident_date)
    if d is None:
        return None
    month_index = (d.year * 12 + (d.month - 1)) + months_after
    year, month0 = divmod(month_index, 12)
    return end_of_month(date(year, month0 + 1, 1))
