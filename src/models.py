"""Machine Learning Pipeline: Fair-Value Pricing & Anomaly Detection (v2).

Changes vs v1 (see reports/KE_HOACH_3_TUAN.md, mục 0.3):
- `deposit_million` is NO LONGER a feature. 82% of listings ask exactly 1 month's rent as
  deposit, so deposit ≈ price -> target leakage (CV R² 0.90 with it vs ~0.54 without).
- Fair price for every listing is an OUT-OF-FOLD prediction (5-fold CV), so the valuation gap
  of a listing never comes from a model that saw that listing during training.
- Metrics are 5-fold CV (not a single split), compared against a naive baseline
  (district median price/m² × size).
- Feature ablation table shows how much each feature group adds.
- Deal labels use data-driven residual percentiles instead of fixed ±15/20/25% cut-offs.
- KTX / sleepbox / ở ghép listings (price per bed) are excluded from the room model and
  labelled SHARED_DORM — in v1 they were the bulk of the "cheapest" (fake scam) listings.

Outputs:
- models/lgbm_fair_price.joblib   {"model", "feature_names", ...} (fit on all data, for the dashboard)
- models/iso_forest_anomaly.joblib
- data/processed/rental_scored_deals.csv
- data/processed/model_report.json (benchmarks, ablation, thresholds) for notebooks & report
"""

import datetime
import json
import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    from sklearn.ensemble import HistGradientBoostingRegressor

from src.config import (
    FINAL_SCHEMA_COLUMNS,
    ISO_FOREST_MODEL_PATH,
    LGBM_MODEL_PATH,
    LISTING_META_COLUMNS,
    MODEL_REPORT_PATH,
    PROCESSED_FULL_CSV,
    PROCESSED_SCORED_CSV,
)
from src.features import build_feature_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Models")
warnings.filterwarnings("ignore", message="X does not have valid feature names")
warnings.filterwarnings("ignore", category=FutureWarning)

RANDOM_STATE = 42
N_FOLDS = 5

# ---------------------------------------------------------------------------
# Feature groups. A "fair price" should depend on the ROOM and its LOCATION only —
# not on who posts it or how the ad is promoted — so seller_type, n_images, is_paid_promo...
# are deliberately excluded here (they are analysed separately in EDA / anomaly rules).
# ---------------------------------------------------------------------------
FEATURE_SIZE = ["size_m2"]
FEATURE_LOCATION = ["dist_to_q1_km", "dist_to_vnuhcm_km"]
FEATURE_AMENITY_V1 = ["has_mezzanine", "has_ac", "is_free_curfew", "has_balcony_window"]
FEATURE_STREET = ["is_main_street", "is_alley"]
# Produced by member B (src/text_features.py, src/external_features.py); used only if present.
FEATURE_TEXT_B = [
    "has_kitchen", "has_washing_machine", "has_parking", "has_elevator", "has_private_wc",
    "female_only", "allow_pet", "shared_room", "elec_price_k", "water_price_k",
]
FEATURE_POI_B = [
    "dist_nearest_university_km", "dist_nearest_metro_km", "dist_nearest_industrial_km", "n_market_1km",
]
FEATURE_CATEGORICAL = ["area_name", "furnishing_status"]
LEAKY_FEATURES = ["deposit_million"]  # kept only for the documented leakage reference row

# Deal-label percentiles on the out-of-fold valuation gap
GAP_Q_EXTREME_LOW = 0.05
GAP_Q_LOW = 0.10
GAP_Q_HIGH = 0.90


def _present(df: pd.DataFrame, cols: List[str]) -> List[str]:
    return [c for c in cols if c in df.columns]


def prepare_training_features(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    categorical_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Build design matrix X (numeric + one-hot categoricals) and target y = price_million."""
    if numeric_cols is None:
        numeric_cols = _present(
            df, FEATURE_SIZE + FEATURE_LOCATION + FEATURE_AMENITY_V1 + FEATURE_STREET + FEATURE_TEXT_B + FEATURE_POI_B
        )
    if categorical_cols is None:
        categorical_cols = _present(df, FEATURE_CATEGORICAL)

    parts = [df[numeric_cols].apply(pd.to_numeric, errors="coerce").astype(float)]
    if categorical_cols:
        parts.append(pd.get_dummies(df[categorical_cols].astype(str), drop_first=True, dtype=float))
    X = pd.concat(parts, axis=1)
    y = df["price_million"].astype(float)
    return X, y, X.columns.tolist()


def _model_zoo() -> Dict[str, Any]:
    """Candidate regressors. Ridge works on log(price) and median-imputes NaN; trees on raw price."""
    zoo: Dict[str, Any] = {
        "Ridge": TransformedTargetRegressor(
            regressor=make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 11))),
            func=np.log,
            inverse_func=np.exp,
        ),
        "RandomForest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestRegressor(n_estimators=300, min_samples_leaf=3, n_jobs=-1, random_state=RANDOM_STATE),
        ),
    }
    if HAS_LIGHTGBM:
        zoo["LightGBM"] = lgb.LGBMRegressor(
            n_estimators=400,
            learning_rate=0.03,
            num_leaves=15,
            min_child_samples=20,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbose=-1,
        )
    else:
        zoo["HistGradientBoosting"] = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.03, max_leaf_nodes=15, random_state=RANDOM_STATE
        )
    return zoo


def _metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    return {
        "R2": round(float(r2_score(y, p)), 4),
        "MAE_Million": round(float(mean_absolute_error(y, p)), 3),
        "RMSE_Million": round(float(np.sqrt(mean_squared_error(y, p))), 3),
        "MAPE_Pct": round(float(mean_absolute_percentage_error(y, p) * 100.0), 2),
    }


def _cv() -> KFold:
    return KFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)


def _oof_predict(model: Any, X: pd.DataFrame, y: pd.Series) -> np.ndarray:
    X_np = np.ascontiguousarray(X.values, dtype=np.float32)
    p = cross_val_predict(model, X_np, y.values, cv=_cv())
    return np.clip(p, 0.3, 30.0)


def baseline_district_median(df: pd.DataFrame) -> np.ndarray:
    """Naive out-of-fold baseline: (district median price per m², computed on training folds) × size."""
    pred = np.zeros(len(df))
    for tr, te in _cv().split(df):
        train = df.iloc[tr]
        med = train.groupby("area_name", observed=True)["price_per_m2_k"].median()
        glob = train["price_per_m2_k"].median()
        rate = df.iloc[te]["area_name"].map(med).astype(float).fillna(glob).values
        pred[te] = rate * df.iloc[te]["size_m2"].values / 1000.0
    return pred


def evaluate_regressors(df: pd.DataFrame) -> Tuple[Dict[str, Dict[str, float]], str, Dict[str, np.ndarray]]:
    """5-fold CV benchmark of baseline + all regressors on the full v2 feature set."""
    X, y, _ = prepare_training_features(df)
    results: Dict[str, Dict[str, float]] = {}
    oof: Dict[str, np.ndarray] = {}

    oof["Baseline_DistrictMedian"] = baseline_district_median(df)
    results["Baseline_DistrictMedian"] = _metrics(y.values, oof["Baseline_DistrictMedian"])
    logger.info(f"[Baseline] {results['Baseline_DistrictMedian']}")

    for name, model in _model_zoo().items():
        logger.info(f"CV training {name} ({N_FOLDS}-fold)...")
        oof[name] = _oof_predict(model, X, y)
        results[name] = _metrics(y.values, oof[name])
        logger.info(f"[{name}] {results[name]}")

    candidates = {k: v for k, v in results.items() if not k.startswith("Baseline")}
    best = max(candidates, key=lambda k: candidates[k]["R2"])
    logger.info(f"Best model by CV R²: {best} ({results[best]['R2']})")
    return results, best, oof


def run_feature_ablation(df: pd.DataFrame, model_name: str) -> List[Dict[str, Any]]:
    """Cumulative feature-group ablation with the chosen model (CV R²/MAE per step)."""
    steps = [
        ("1. Diện tích + Quận/Huyện", FEATURE_SIZE, ["area_name"]),
        ("2. + Khoảng cách tới Q1 & ĐHQG", FEATURE_SIZE + FEATURE_LOCATION, ["area_name"]),
        ("3. + Nội thất & tiện ích regex v1", FEATURE_SIZE + FEATURE_LOCATION + FEATURE_AMENITY_V1, FEATURE_CATEGORICAL),
        ("4. + Mặt tiền / hẻm", FEATURE_SIZE + FEATURE_LOCATION + FEATURE_AMENITY_V1 + FEATURE_STREET, FEATURE_CATEGORICAL),
    ]
    text_b, poi_b = _present(df, FEATURE_TEXT_B), _present(df, FEATURE_POI_B)
    if text_b:
        steps.append(("5. + Tiện ích mở rộng (B)", steps[-1][1] + text_b, FEATURE_CATEGORICAL))
    if poi_b:
        steps.append(("6. + Khoảng cách POI OSM (B)", steps[-1][1] + poi_b, FEATURE_CATEGORICAL))
    # Documented leakage reference: full feature set + deposit
    steps.append(("THAM KHẢO: + tiền cọc (RÒ RỈ — không dùng)", steps[-1][1] + LEAKY_FEATURES, FEATURE_CATEGORICAL))

    model = _model_zoo()[model_name]
    rows = []
    for label, num, cat in steps:
        X, y, cols = prepare_training_features(df, _present(df, num), _present(df, cat))
        m = _metrics(y.values, _oof_predict(clone(model), X, y))
        rows.append({"step": label, "n_features": len(cols), **m})
        logger.info(f"[Ablation] {label}: R²={m['R2']} MAE={m['MAE_Million']}")
    return rows


def train_anomaly_detector(df: pd.DataFrame) -> Tuple[IsolationForest, np.ndarray, np.ndarray]:
    """Isolation Forest on out-of-fold residual + unit price + size + distance."""
    anomaly_features = ["valuation_gap_pct", "price_per_m2_k", "size_m2", "dist_to_q1_km"]
    X_iso = df[anomaly_features].fillna(0).values

    iso_forest = IsolationForest(
        contamination=0.05,
        random_state=RANDOM_STATE,
        n_estimators=200,
        n_jobs=-1,
    )
    labels = iso_forest.fit_predict(X_iso)  # -1 anomaly, 1 inlier
    scores = -iso_forest.score_samples(X_iso)  # higher = more anomalous
    return iso_forest, labels, scores


def assign_case_study_labels(df: pd.DataFrame) -> Tuple[pd.Series, Dict[str, float]]:
    """Label listings from the OUT-OF-FOLD valuation gap distribution.

    - SCAM_RISK  ("Nghi vấn bất thường – cần kiểm chứng"): gap in the cheapest 5% AND
                 (Isolation Forest anomaly OR "Môi giới trá hình"). NOT proof of fraud.
    - GOOD_DEAL  ("Rẻ hơn mặt bằng"): gap in the cheapest 10%, not flagged above.
    - OVERPRICED ("Đắt hơn mặt bằng"): gap in the most expensive 10%.
    - FAIR_PRICE: the rest.
    - SHARED_DORM (set in run_full_modeling_pipeline): KTX / sleepbox / ở ghép, priced per bed,
                 excluded from the room model.
    The four room label codes are unchanged from v1 so the Streamlit dashboard keeps working.
    """
    gap = df["valuation_gap_pct"]
    thr = {
        "q05_extreme_low": round(float(gap.quantile(GAP_Q_EXTREME_LOW)), 2),
        "q10_low": round(float(gap.quantile(GAP_Q_LOW)), 2),
        "q90_high": round(float(gap.quantile(GAP_Q_HIGH)), 2),
    }
    suspicious_context = df["is_iso_anomaly"] | (df["seller_type"].astype(str) == "Môi giới trá hình")

    labels = pd.Series("FAIR_PRICE", index=df.index)
    labels[gap >= thr["q90_high"]] = "OVERPRICED"
    labels[gap <= thr["q10_low"]] = "GOOD_DEAL"
    labels[(gap <= thr["q05_extreme_low"]) & suspicious_context] = "SCAM_RISK"
    return labels.astype("category"), thr


def run_full_modeling_pipeline(df_input: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Benchmark -> ablation -> OOF fair price -> anomaly -> labels -> export."""
    if df_input is None:
        if not PROCESSED_FULL_CSV.exists():
            df_input = build_feature_pipeline()
        else:
            df_input = pd.read_csv(PROCESSED_FULL_CSV, low_memory=False)

    df_all = df_input.reset_index(drop=True).copy()
    # KTX / sleepbox / ở ghép are priced per bed -> not comparable with whole-room prices.
    if "is_shared_or_dorm" in df_all.columns:
        dorm_mask = df_all["is_shared_or_dorm"].fillna(0).astype(int) == 1
    else:
        dorm_mask = pd.Series(False, index=df_all.index)
    df = df_all[~dorm_mask].reset_index(drop=True).copy()
    df_dorm = df_all[dorm_mask].copy()
    logger.info(
        f"Starting ML modeling pipeline with {len(df)} room listings "
        f"({len(df_dorm)} KTX/ở ghép listings excluded and labelled SHARED_DORM)..."
    )

    # Step 1: CV benchmark & model choice
    benchmarks, best_name, oof = evaluate_regressors(df)

    # Step 2: Ablation with the chosen model
    ablation = run_feature_ablation(df, best_name)

    # Step 3: Final model fit on all data (for the dashboard). OOF predictions are used for scoring.
    X, y, feature_names = prepare_training_features(df)
    final_model = _model_zoo()[best_name]
    final_model.fit(np.ascontiguousarray(X.values, dtype=np.float32), y.values)
    joblib.dump(
        {
            "model": final_model,
            "model_name": best_name,
            "feature_names": feature_names,
            "cv_metrics": benchmarks[best_name],
            "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "n_train": int(len(df)),
        },
        LGBM_MODEL_PATH,
    )
    logger.info(f"Saved final {best_name} model ({len(feature_names)} features) to {LGBM_MODEL_PATH}")

    # Step 4: Out-of-fold fair price & valuation gap
    df["predicted_price"] = np.round(oof[best_name], 2)
    df["valuation_gap_pct"] = np.round((df["price_million"] - df["predicted_price"]) / df["predicted_price"] * 100.0, 2)

    # Step 5: Anomaly detector
    iso_model, anomaly_preds, anomaly_scores = train_anomaly_detector(df)
    df["is_iso_anomaly"] = anomaly_preds == -1
    df["anomaly_score"] = np.round(anomaly_scores, 4)
    joblib.dump(iso_model, ISO_FOREST_MODEL_PATH)
    logger.info(f"Saved Isolation Forest model to {ISO_FOREST_MODEL_PATH}")

    # Step 6: Decision labels
    df["deal_status"], thresholds = assign_case_study_labels(df)

    # Re-attach the excluded KTX / ở ghép listings (no fair price, own label)
    if len(df_dorm):
        df_dorm["predicted_price"] = np.nan
        df_dorm["valuation_gap_pct"] = np.nan
        df_dorm["is_iso_anomaly"] = False
        df_dorm["anomaly_score"] = np.nan
        df_dorm["deal_status"] = "SHARED_DORM"
        df = pd.concat([df.assign(deal_status=df["deal_status"].astype(str)), df_dorm], ignore_index=True)
    df["deal_status"] = df["deal_status"].astype("category")
    deal_breakdown = {k: int(v) for k, v in df["deal_status"].value_counts().items()}
    logger.info(f"Case Study Decision Breakdown: {deal_breakdown} | thresholds: {thresholds}")

    # Step 7: Export — 26 standard columns first, then v2 extended columns
    extra_cols = LISTING_META_COLUMNS + FEATURE_TEXT_B + FEATURE_POI_B + ["is_iso_anomaly", "anomaly_score"]
    export_cols = _present(df, FINAL_SCHEMA_COLUMNS) + [c for c in _present(df, extra_cols) if c not in FINAL_SCHEMA_COLUMNS]
    df_export = df[export_cols].copy()
    df_export.to_csv(PROCESSED_SCORED_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Exported {len(df_export)} scored listings ({len(export_cols)} cols) to {PROCESSED_SCORED_CSV}")

    summary = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "n_listings": int(len(df)),
        "n_model_listings": int(len(df) - len(df_dorm)),
        "n_shared_dorm_excluded": int(len(df_dorm)),
        "cv": f"{N_FOLDS}-fold KFold(shuffle=True, random_state={RANDOM_STATE})",
        "target": "price_million",
        "excluded_leaky_features": LEAKY_FEATURES,
        "features_used": feature_names,
        "best_model": best_name,
        "benchmarks": benchmarks,
        "best_metrics": benchmarks[best_name],
        "ablation": ablation,
        "deal_thresholds_gap_pct": thresholds,
        "deal_breakdown": deal_breakdown,
        "total_scored_records": int(len(df_export)),
    }
    with open(MODEL_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"Model report saved to {MODEL_REPORT_PATH}")
    return df_export, summary


if __name__ == "__main__":
    df_scored, summary = run_full_modeling_pipeline()
    print("\n--- MODEL BENCHMARK (5-fold CV) ---")
    for m, met in summary["benchmarks"].items():
        print(f"{m}: {met}")
    print("\n--- FEATURE ABLATION ---")
    for row in summary["ablation"]:
        print(row)
    print("\n--- DEAL STATUS SUMMARY ---")
    print(summary["deal_breakdown"], summary["deal_thresholds_gap_pct"])
