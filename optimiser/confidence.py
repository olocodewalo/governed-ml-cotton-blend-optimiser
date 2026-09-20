"""Confidence policy (model governance policy, section 6).

HIGH (auto-suggestable) only if ALL hold:
  * every predicted mean is inside the spec band and no hard constraint is violated,
  * the CSP P10 clears the CSP floor,
  * the CSP P10-P90 band is narrower than ``CONF_MAX_CSP_BAND_WIDTH``,
  * the blend is inside the model's training support.
An out-of-support blend is never HIGH: at best MEDIUM. Anything with a violated
limit is LOW. Below HIGH, a master decision is mandatory.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import CONF_MAX_CSP_BAND_WIDTH


@dataclass
class Confidence:
    level: str                 # HIGH | MEDIUM | LOW
    reasons: list[str]
    support_ratio: float | None

    @property
    def auto_suggestable(self) -> bool:
        return self.level == "HIGH"

    @property
    def summary(self) -> str:
        head = {"HIGH": "eligible for auto-suggest",
                "MEDIUM": "master review required",
                "LOW": "do not run without a master decision"}[self.level]
        return f"{head}: " + "; ".join(self.reasons)


def blend_support_ratio(result, model) -> float | None:
    if not getattr(model, "train_ref_", None):
        return None
    row = pd.DataFrame([result.profile], columns=model.features)
    return float(model.support_ratio(row)[0])


def assess(result, spec: dict, model) -> Confidence:
    csp = result.predicted["csp"]
    width = csp["p90"] - csp["p10"]
    ratio = blend_support_ratio(result, model)

    violated = [b for b in result.binding_constraints if b.startswith("VIOLATED")]
    if not result.in_band or violated:
        return Confidence("LOW", violated or ["predicted quality outside the spec band"], ratio)

    reasons, blockers = [], []
    if csp["p10"] >= spec["min_csp"]:
        reasons.append(f"CSP P10 {csp['p10']:.0f} clears floor {spec['min_csp']}")
    else:
        blockers.append(f"CSP P10 {csp['p10']:.0f} below floor {spec['min_csp']}")
    if width < CONF_MAX_CSP_BAND_WIDTH:
        reasons.append(f"CSP band width {width:.0f} < {CONF_MAX_CSP_BAND_WIDTH:.0f}")
    else:
        blockers.append(f"CSP band width {width:.0f} >= {CONF_MAX_CSP_BAND_WIDTH:.0f}")
    if ratio is None:
        blockers.append("training-support check unavailable for this model")
    elif ratio <= 1.0:
        reasons.append(f"inside training support (distance ratio {ratio:.2f})")
    else:
        blockers.append(f"OUT OF TRAINING SUPPORT (distance ratio {ratio:.2f} > 1) -- model is extrapolating")

    if blockers:
        return Confidence("MEDIUM", blockers + reasons, ratio)
    return Confidence("HIGH", reasons, ratio)
