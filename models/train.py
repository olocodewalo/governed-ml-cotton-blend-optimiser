"""Train the ML quality model, evaluate it, save a SHAP chart, register it.

Run: ``python -m models.train``  (or ``make train``)
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd

from config import ARTIFACTS_DIR, DOCS_DIR, QUALITY_TARGETS
from models import registry
from models.dataset import build_xy, data_hash, load_bales, load_laydowns, train_test_split_by_time
from models.quality_model import QualityModel

warnings.filterwarnings("ignore", category=UserWarning)


def _metrics(y_true: pd.DataFrame, pred: pd.DataFrame) -> dict:
    m = {}
    for t in QUALITY_TARGETS:
        err = pred[t].to_numpy() - y_true[t].to_numpy()
        mae = float(np.mean(np.abs(err)))
        rmse = float(np.sqrt(np.mean(err ** 2)))
        # coverage of the P10..P90 band (target ~0.80 if well calibrated)
        inside = ((y_true[t].to_numpy() >= pred[f"{t}_p10"].to_numpy())
                  & (y_true[t].to_numpy() <= pred[f"{t}_p90"].to_numpy()))
        m[t] = dict(mae=round(mae, 3), rmse=round(rmse, 3),
                    pi_coverage=round(float(np.mean(inside)), 3),
                    mean_abs_target=round(float(np.mean(np.abs(y_true[t]))), 2))
    return m


def _shap_chart(model: QualityModel, X: pd.DataFrame, path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import shap
    except Exception as e:  # pragma: no cover
        print(f"[shap] skipped ({e})")
        return False
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    for ax, t in zip(axes.ravel(), QUALITY_TARGETS):
        expl = shap.TreeExplainer(model.mean_[t])
        sv = expl.shap_values(X)
        plt.sca(ax)
        shap.summary_plot(sv, X, show=False, plot_size=None, plot_type="bar")
        ax.set_title(f"SHAP importance -> {t}")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return True


def main() -> None:
    bales = load_bales()
    laydowns = load_laydowns()
    train_ld, test_ld = train_test_split_by_time(laydowns, test_frac=0.2)

    X_tr, y_tr = build_xy(train_ld, bales)
    X_te, y_te = build_xy(test_ld, bales)

    version = registry.next_version()
    model = QualityModel(version=version).fit(X_tr, y_tr)

    pred_te = model.predict(X_te)
    metrics = _metrics(y_te, pred_te)

    artifact_path = ARTIFACTS_DIR / f"quality_model_{version}.joblib"
    model.save(artifact_path)
    # also save/refresh the "current" pointer used by app + optimiser + eval
    model.save(ARTIFACTS_DIR / "quality_model_current.joblib")

    DOCS_DIR.mkdir(exist_ok=True)
    have_shap = _shap_chart(model, X_te, DOCS_DIR / "shap_summary.png")

    dh = data_hash(train_ld, bales)
    entry = registry.register(
        version=version,
        artifact_path=str(artifact_path),
        training_data_hash=dh,
        metrics=metrics,
        n_train=len(X_tr),
        n_test=len(X_te),
        notes="LightGBM mean + P10/P90 quantile heads; chronological split.",
    )

    # optional MLflow logging
    try:
        import mlflow
        mlflow.set_experiment("cotton_blend_quality")
        with mlflow.start_run(run_name=version):
            mlflow.log_param("data_hash", dh)
            for t, mm in metrics.items():
                for k, v in mm.items():
                    mlflow.log_metric(f"{t}_{k}", v)
    except Exception as e:  # pragma: no cover
        print(f"[mlflow] skipped ({e})")

    print(json.dumps(dict(version=version, metrics=metrics,
                          shap_chart=have_shap, registry_status=entry["status"]), indent=2))


if __name__ == "__main__":
    main()
