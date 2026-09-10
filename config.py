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

# --- LLM explainer ----------------------------------------------------------
ANTHROPIC_MODEL = "claude-sonnet-5"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"


def anthropic_key() -> str | None:
    return os.environ.get(ANTHROPIC_API_KEY_ENV)
