"""GROUND TRUTH physics of spun-yarn quality as a function of a blend's fibre profile.

This module is the *single source of truth* for how a bale laydown turns into
spun-yarn quality. The synthetic data generator uses it to label historical
laydowns; the ML model in ``models/`` must learn to approximate it without ever
seeing it; the eval harness scores the ML model against it.

Everything here is a deliberately-simplified but *directionally correct* model of
real cotton spinning physics. Key non-linearities (the whole reason an ML model
earns its keep):

  * Short-fibre content (SFC) hurts strength and evenness with an accelerating
    (power > 1) penalty -- a blend at 13% SFC is far worse than twice as bad as
    one at 9%.
  * Micronaire *variance* across the blend (mixing coarse and fine fibres) hurts
    evenness and neps super-linearly, independent of the mean micronaire.
  * Neps (a big chunk of "imperfections") come from BOTH low micronaire
    (immature, tangle-prone fibre) and high SFC, and the two interact.

Inputs are blend-aggregate quantities (weighted means / weighted variances),
computed by :func:`data.features.blend_profile`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- Tunable ground-truth coefficients ---------------------------------------
# Named so the data card / docs can cite them. Do not "improve" these casually:
# the golden-set targets in eval/ are calibrated to this exact formula.

A_STRENGTH = 50.0        # CSP gain per g/tex of weighted strength
B_STAPLE = 30.0          # CSP gain per mm of weighted staple length
C_SFC = 20.0             # CSP loss scale for short-fibre content
C_SFC_POW = 1.65         # ...raised to this power (super-linear)
D_MICVAR = 155.0         # CSP loss scale for micronaire spread
D_MICVAR_POW = 1.30
CSP_INTERCEPT = 150.0
CSP_UNIFORMITY = 8.0     # CSP gain per uniformity %-point above 80

E_U = 6.9                # U% intercept
F_SFC_U = 0.145          # U% per SFC point ...
F_SFC_U_POW = 1.35       # ...super-linear
G_MICVAR_U = 3.1         # U% per unit micronaire spread ^ pow
G_MICVAR_U_POW = 1.20
U_TRASH = 0.25           # U% per trash %-point

H_IMPERF = 85.0          # imperfections scale on the neps proxy
IMPERF_INTERCEPT = 30.0
IMPERF_TRASH = 14.0

K_ENDS = 0.9             # ends-down scale on a "spinnability deficit" term
ENDS_INTERCEPT = 2.0

# Noise (1 sigma) added when *generating* historical labels -- represents
# unmodelled process variation (humidity, machine state, operator).
NOISE_SIGMA = dict(csp=28.0, u_pct=0.16, imperfections=14.0, ends_down=0.5)


@dataclass
class QualityOutcome:
    csp: float
    u_pct: float
    imperfections: float
    ends_down: float

    def as_dict(self) -> dict:
        return dict(csp=self.csp, u_pct=self.u_pct,
                    imperfections=self.imperfections, ends_down=self.ends_down)


def _neps_proxy(sfc: float, micronaire_mean: float, micronaire_var: float) -> float:
    """Dimensionless neps-formation tendency.

    Rises with SFC (tangle-prone material), with distance of mean micronaire
    from the ideal ~4.0 (immature *or* over-coarse fibre), and with micronaire
    spread. SFC and immaturity interact multiplicatively.
    """
    sfc_term = (max(sfc, 0.0) / 6.0) ** 2.0
    maturity_gap = ((micronaire_mean - 4.0) / 1.0) ** 2.0
    spread_term = 1.0 + 2.2 * (max(micronaire_var, 0.0) ** 1.15)
    return sfc_term * (1.0 + 0.55 * maturity_gap) * spread_term


def predict_quality(profile: dict, rng: np.random.Generator | None = None,
                    add_noise: bool = False) -> QualityOutcome:
    """Ground-truth yarn quality for a blend-aggregate ``profile``.

    ``profile`` keys (see :func:`data.features.blend_profile`):
        w_mean_strength_gtex, w_mean_staple_length_mm, w_mean_uniformity_pct,
        w_mean_short_fibre_content_pct, w_mean_micronaire, w_mean_trash_pct,
        w_var_micronaire, w_var_short_fibre_content_pct
    """
    s = profile["w_mean_strength_gtex"]
    stap = profile["w_mean_staple_length_mm"]
    unif = profile["w_mean_uniformity_pct"]
    sfc = profile["w_mean_short_fibre_content_pct"]
    mic = profile["w_mean_micronaire"]
    trash = profile["w_mean_trash_pct"]
    mic_var = profile["w_var_micronaire"]
    sfc_var = profile.get("w_var_short_fibre_content_pct", 0.0)

    sfc_penalty = C_SFC * (max(sfc - 5.0, 0.0) ** C_SFC_POW)
    micvar_penalty = D_MICVAR * (max(mic_var, 0.0) ** D_MICVAR_POW)

    csp = (
        CSP_INTERCEPT
        + A_STRENGTH * s
        + B_STAPLE * stap
        + CSP_UNIFORMITY * (unif - 80.0)
        - sfc_penalty
        - micvar_penalty
    )

    u_pct = (
        E_U
        + F_SFC_U * (max(sfc - 4.0, 0.0) ** F_SFC_U_POW)
        + G_MICVAR_U * (max(mic_var, 0.0) ** G_MICVAR_U_POW)
        + U_TRASH * trash
        + 0.04 * max(sfc_var, 0.0)
        - 0.05 * (unif - 80.0)
    )

    neps = _neps_proxy(sfc, mic, mic_var)
    imperfections = IMPERF_INTERCEPT + H_IMPERF * neps + IMPERF_TRASH * trash

    # Ends-down: spinning breaks rise when strength is low relative to what the
    # count needs and when there is a lot of short fibre; interaction term.
    spinnability_deficit = max(30.5 - s, 0.0) + 0.6 * max(sfc - 8.0, 0.0)
    ends_down = (
        ENDS_INTERCEPT
        + K_ENDS * spinnability_deficit
        + 0.12 * micvar_penalty / 10.0
    )

    if add_noise:
        rng = rng or np.random.default_rng()
        csp += rng.normal(0, NOISE_SIGMA["csp"])
        u_pct += rng.normal(0, NOISE_SIGMA["u_pct"])
        imperfections += rng.normal(0, NOISE_SIGMA["imperfections"])
        ends_down += rng.normal(0, NOISE_SIGMA["ends_down"])

    return QualityOutcome(
        csp=round(float(csp), 1),
        u_pct=round(float(max(u_pct, 4.0)), 2),
        imperfections=round(float(max(imperfections, 0.0)), 0),
        ends_down=round(float(max(ends_down, 0.0)), 2),
    )
