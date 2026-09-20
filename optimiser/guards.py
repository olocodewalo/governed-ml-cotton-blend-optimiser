"""Pre-run guards the optimiser enforces before it will recommend anything.

* Price freshness (RAID R4): refuse to optimise against bale prices older than
  ``PRICE_MAX_AGE_DAYS`` at the planning date.
* Origin caps (RAID R9): contamination-prone origins are capped as a blend
  share regardless of price. The LP adds them as hard constraints, the GA as
  penalties, and ``evaluate_blend`` flags any violation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import ORIGIN_MAX_FRACTION, PRICE_MAX_AGE_DAYS


class StalePriceError(RuntimeError):
    """Raised when inventory prices are too old (or undated) to optimise against."""


def price_age_days(inventory: pd.DataFrame, as_of) -> pd.Series:
    if "price_as_of" not in inventory:
        raise StalePriceError("inventory has no price_as_of column -- price freshness unknown")
    as_of = pd.Timestamp(as_of).normalize()
    return (as_of - pd.to_datetime(inventory["price_as_of"]).dt.normalize()).dt.days


def check_price_freshness(inventory: pd.DataFrame, as_of,
                          max_age_days: int = PRICE_MAX_AGE_DAYS) -> None:
    age = price_age_days(inventory, as_of)
    stale = inventory.loc[age > max_age_days, "bale_id"]
    future = inventory.loc[age < 0, "bale_id"]
    if len(stale):
        raise StalePriceError(
            f"{len(stale)} of {len(inventory)} bale prices are older than {max_age_days} days "
            f"at planning date {pd.Timestamp(as_of).date()} (oldest {int(age.max())} days, "
            f"e.g. {', '.join(stale.head(3))}); refresh the price sheet before optimising")
    if len(future):
        raise StalePriceError(
            f"{len(future)} bale prices are dated after the planning date "
            f"{pd.Timestamp(as_of).date()}; check the planning date")


def origin_caps(caps: dict | None = None) -> dict:
    return dict(ORIGIN_MAX_FRACTION if caps is None else caps)


def origin_cap_violations(profile: dict, caps: dict, tol: float = 1e-4) -> list[str]:
    out = []
    for origin, cap in caps.items():
        frac = profile.get(f"origin_frac_{origin}", 0.0)
        if frac > cap + tol:
            out.append(f"VIOLATED origin cap {origin}: {frac:.3f} > {cap}")
        elif frac >= cap * 0.98:
            out.append(f"binding origin cap {origin}: {frac:.3f} ~ max {cap}")
    return out


def origin_masks(inventory: pd.DataFrame, caps: dict) -> dict:
    origin = inventory["origin"].to_numpy()
    return {o: (origin == o) for o in caps}


def origin_excess(weights: np.ndarray, masks: dict, caps: dict) -> float:
    """Total share above the caps for a normalised weight vector (GA penalty)."""
    return float(sum(max(0.0, float(weights[m].sum()) - caps[o]) for o, m in masks.items()))
