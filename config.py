"""Central configuration: paths, fibre properties, yarn-count spec bands.

Single import point so every module agrees on column names and file locations.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "artifacts"
DOCS_DIR = ROOT / "docs"
MODEL_REGISTRY = ARTIFACTS_DIR / "model_registry.json"
DECISIONS_DB = ARTIFACTS_DIR / "decisions.sqlite"

BALES_PARQUET = DATA_DIR / "bales.parquet"
LAYDOWNS_PARQUET = DATA_DIR / "laydowns.parquet"

ARTIFACTS_DIR.mkdir(exist_ok=True)

RANDOM_SEED = 20260910

# --- Fibre properties measured per bale (HVI / AFIS proxies) --------------------
FIBRE_PROPS = [
    "micronaire",
    "staple_length_mm",
    "strength_gtex",
    "uniformity_pct",
    "short_fibre_content_pct",
    "trash_pct",
    "maturity_ratio",
]

ORIGINS = [
    "India_Shankar6",
    "US_Pima",
    "West_African",
    "Egyptian_Giza",
]

# Targets predicted by the ML quality model
QUALITY_TARGETS = ["csp", "u_pct", "imperfections", "ends_down"]

# --- Yarn-count spec bands ----------------------------------------------------
# Finer counts (higher Ne) need better fibre and tolerate less irregularity.
# band = dict(min_csp, max_u_pct, max_imperfections, max_ends_down)
YARN_COUNT_SPECS = {
    "20s_Ne": dict(min_csp=2080, max_u_pct=10.3, max_imperfections=380, max_ends_down=9.0),
    "30s_Ne": dict(min_csp=2180, max_u_pct=9.9, max_imperfections=360, max_ends_down=9.0),
    "40s_Ne": dict(min_csp=2270, max_u_pct=9.6, max_imperfections=340, max_ends_down=10.0),
    "60s_Ne": dict(min_csp=2350, max_u_pct=9.3, max_imperfections=330, max_ends_down=12.0),
}

# --- Long-term-blend deviation limits (consistency constraint) ----------------
LTB_MICRONAIRE_TOL = 0.2
LTB_STRENGTH_TOL = 1.5
ROLLING_WINDOW = 30
MAX_BALES_IN_LAYDOWN = 45
MIN_BALES_IN_LAYDOWN = 30

# --- Contamination control (RAID R9) ----------------------------------------
# Hard cap on the blend share of contamination-prone origins, applied regardless
# of price (see explainer/kb/07 and kb/15).
ORIGIN_MAX_FRACTION = {"West_African": 0.30}

# --- Price freshness (RAID R4) ----------------------------------------------
# The optimiser refuses to run on bale prices older than this at planning time.
PRICE_MAX_AGE_DAYS = 7

# --- Model governance (docs/model_governance_policy.md) ---------------------
# Section 3: candidate -> approved acceptance thresholds, on the golden set.
ACCEPTANCE_THRESHOLDS = {
    "quality.csp.mae": ("max", 35.0),
    "quality.u_pct.mae": ("max", 0.22),
    "quality.imperfections.mae": ("max", 28.0),
    "quality.ends_down.mae": ("max", 0.7),
    "quality.csp.pi_coverage": ("range", (0.70, 0.90)),
    "quality.u_pct.pi_coverage": ("range", (0.70, 0.90)),
    "quality.imperfections.pi_coverage": ("range", (0.70, 0.90)),
    "quality.ends_down.pi_coverage": ("range", (0.70, 0.90)),
    "decision.agreement": ("min", 0.90),
    "decision.false_accept_rate": ("max", 0.05),
    "optimiser.optimiser_blend_in_band_rate": ("min", 0.90),
}

# Section 6: confidence policy. HIGH (auto-suggestable) needs all of these.
CONF_MAX_CSP_BAND_WIDTH = 250.0
# Out-of-support: kNN distance to training blends, as a multiple of the
# training set's own 99th-percentile kNN distance.
SUPPORT_KNN_K = 5
SUPPORT_QUANTILE = 0.99

# Section 5: retrain triggers.
PSI_ALERT = 0.2
PSI_BINS = 10
ROLLING_MAE_WINDOW = 8          # ~4 weeks of laydowns (one every ~3.6 days)
ROLLING_MAE_ALERT_RATIO = 1.5
CORRECTIONS_RETRAIN_TRIGGER = 20
PSI_KEY_FEATURES = [
    "w_mean_micronaire",
    "w_mean_staple_length_mm",
    "w_mean_strength_gtex",
    "w_mean_short_fibre_content_pct",
    "w_var_micronaire",
    "n_bales_effective",
]

# --- LLM explainer ----------------------------------------------------------
ANTHROPIC_MODEL = "claude-sonnet-5"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"


def anthropic_key() -> str | None:
    return os.environ.get(ANTHROPIC_API_KEY_ENV)
