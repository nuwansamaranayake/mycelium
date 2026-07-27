"""Deterministic freshness labels: staleness is arithmetic, never a model opinion.

The label is computed from the document timestamp supplied at ingest against a reference
time carried by the request. This module never calls datetime.now(): the eval path passes
the golden corpus reference time, and only the live API defaults the reference to now
(explicitly, in the route). A document dated in the future of the reference clamps to age 0.

Thresholds (days): fresh < 30, aging 30..180 inclusive, stale > 180.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

FRESH_BELOW_DAYS = 30
AGING_MAX_DAYS = 180


class FreshnessLabel(BaseModel):
    label: str            # fresh | aging | stale
    age_days: int
    as_of: datetime


def freshness(doc_timestamp: datetime, as_of: datetime) -> FreshnessLabel:
    if doc_timestamp.tzinfo is None or as_of.tzinfo is None:
        raise ValueError("freshness requires timezone-aware datetimes; naive input is a bug")
    age_days = max(0, (as_of - doc_timestamp).days)
    if age_days < FRESH_BELOW_DAYS:
        label = "fresh"
    elif age_days <= AGING_MAX_DAYS:
        label = "aging"
    else:
        label = "stale"
    return FreshnessLabel(label=label, age_days=age_days, as_of=as_of)
