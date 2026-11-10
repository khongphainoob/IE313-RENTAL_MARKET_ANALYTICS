"""Machine Learning Pipeline: Fair-Value Pricing & Anomaly Detection.

Implements:
1. Benchmark Regression Models (Ridge, Random Forest, LightGBM) to predict fair price (\hat{y}).
2. Valuation Gap residual analysis: valuation_gap_pct = ((price - predicted) / predicted) * 100.
3. Isolation Forest Anomaly Detection.
4. Business Decision Labeling: GOOD_DEAL, SCAM_RISK, FAIR_PRICE, OVERPRICED.
5. Exports models to models/ and scored dataset to rental_scored_deals.csv.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

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


FEATURE_NUMERICAL = [
    "size_m2",
    "dist_to_q1_km",
    "dist_to_vnuhcm_km",
    "deposit_million",
]

FEATURE_BINARY = [
    "has_mezzanine",
    "has_ac",
    "is_free_curfew",
    "has_balcony_window",
]

FEATURE_CATEGORICAL = [
    "area_name",
    "furnishing_status",
    "seller_type",
]


def prepare_training_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Encode categorical features and assemble design matrix X and target y."""
    df_feat = df.copy()

    # Create dummy/one-hot variables for categoricals
    df_encoded = pd.get_dummies(df_feat[FEATURE_CATEGORICAL], drop_first=True, dtype=float)

    feature_cols = FEATURE_NUMERICAL + FEATURE_BINARY + df_encoded.columns.tolist()
    X = pd.concat([df_feat[FEATURE_NUMERICAL + FEATURE_BINARY].astype(float), df_encoded], axis=1)
    y = df_feat["price_million"].astype(float)

    return X, y, feature_cols


def evaluate_regressors(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[Dict[str, Any], Any, Dict[str, float]]:
    """Train and benchmark Ridge, Random Forest, and LightGBM / HistGradientBoosting."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # Convert to contiguous float32 numpy arrays for compatibility with NumPy 2.x / LightGBM
    X_train_np = np.ascontiguousarray(X_train.values, dtype=np.float32)
    y_train_np = np.ascontiguousarray(y_train.values, dtype=np.float32)
    X_test_np = np.ascontiguousarray(X_test.values, dtype=np.float32)
    y_test_np = np.ascontiguousarray(y_test.values, dtype=np.float32)

    models_dict = {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(
            n_estimators=120, max_depth=14, random_state=random_state, n_jobs=-1
        ),
    }

    if HAS_LIGHTGBM:
        models_dict["LightGBM"] = lgb.LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=31,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )
    else:
        models_dict["HistGradientBoosting"] = HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_leaf_nodes=31, random_state=random_state
        )

    benchmark_results = {}
    best_model_name = None
    best_r2 = -float("inf")
    best_model_obj = None

    for name, model in models_dict.items():
        logger.info(f"Training {name}...")
        model.fit(X_train_np, y_train_np)
        y_pred = model.predict(X_test_np)
        y_pred = np.clip(y_pred, 0.5, 30.0)

        r2 = r2_score(y_test_np, y_pred)
        mae = mean_absolute_error(y_test_np, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test_np, y_pred))
        mape = mean_absolute_percentage_error(y_test_np, y_pred) * 100.0

        benchmark_results[name] = {
            "R2": round(r2, 4),
            "MAE_Million": round(mae, 3),
            "RMSE_Million": round(rmse, 3),
            "MAPE_Pct": round(mape, 2),
        }
        logger.info(f"[{name}] R²: {r2:.4f} | MAE: {mae:.3f}M | RMSE: {rmse:.3f}M | MAPE: {mape:.2f}%")

        if r2 > best_r2:
            best_r2 = r2
            best_model_name = name
            best_model_obj = model

    logger.info(f"Best performing model: {best_model_name} (R² = {best_r2:.4f})")
    return benchmark_results, best_model_obj, benchmark_results[best_model_name]


def train_anomaly_detector(df: pd.DataFrame) -> Tuple[IsolationForest, np.ndarray]:
    """Train Isolation Forest on price residuals and economic ratios."""
    anomaly_features = ["valuation_gap_pct", "price_per_m2_k", "dist_to_q1_km"]
    X_iso = df[anomaly_features].fillna(0).values

    iso_forest = IsolationForest(
        contamination=0.04,
        random_state=42,
        n_estimators=150,
        n_jobs=-1,
    )
    anomaly_labels = iso_forest.fit_predict(X_iso)  # -1 for anomaly, 1 for inlier
    return iso_forest, anomaly_labels


def assign_case_study_decision(row: pd.Series) -> str:
    """Classify listing into Scam, Good Deal, Fair Price, or Overpriced."""
    gap = row["valuation_gap_pct"]
    seller = str(row.get("seller_type", ""))
    is_anomaly = row.get("is_iso_anomaly", False)

    # 1. SCAM_RISK: Extremely underpriced (>25% below fair value) + deceptive broker OR abnormal multidimensional anomaly
    if gap <= -25.0 and (seller == "Môi giới trá hình" or is_anomaly):
        return "SCAM_RISK"

    # 2. GOOD_DEAL: Underpriced (>15% below fair value) + genuine direct owner
    if gap <= -15.0 and seller == "Chính chủ":
        return "GOOD_DEAL"

    # 3. OVERPRICED: Over 20% above fair value
    if gap >= 20.0:
        return "OVERPRICED"

    # 4. FAIR_PRICE: Normal market equilibrium
    return "FAIR_PRICE"


def run_full_modeling_pipeline(df_input: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Execute end-to-end regression, residual valuation gap, anomaly detection, and export."""
    if df_input is None:
        if not PROCESSED_FULL_CSV.exists():
            df_input = build_feature_pipeline()
        else:
            df_input = pd.read_csv(PROCESSED_FULL_CSV)

    df = df_input.copy()
    logger.info(f"Starting ML modeling pipeline with {len(df)} listings...")

    # Step 1: Feature preparation & Regression Benchmark
    X, y, feature_names = prepare_training_features(df)
    benchmarks, best_model, best_metrics = evaluate_regressors(X, y)

    # Save best regression model
    joblib.dump({"model": best_model, "feature_names": feature_names}, LGBM_MODEL_PATH)
    logger.info(f"Saved best regression model to {LGBM_MODEL_PATH}")

    # Predict fair-value price for entire dataset
    X_full_np = np.ascontiguousarray(X.values, dtype=np.float32)
    df["predicted_price"] = np.round(best_model.predict(X_full_np), 2)
    # Clip predicted price to reasonable minimum
    df["predicted_price"] = np.clip(df["predicted_price"], 0.5, 30.0)

    # Step 2: Valuation Gap residual percentage
    df["valuation_gap_pct"] = np.round(
        ((df["price_million"] - df["predicted_price"]) / df["predicted_price"]) * 100.0,
        2,
    )

    # Step 3: Train Anomaly Detector
    iso_model, anomaly_preds = train_anomaly_detector(df)
    df["is_iso_anomaly"] = (anomaly_preds == -1)

    joblib.dump(iso_model, ISO_FOREST_MODEL_PATH)
    logger.info(f"Saved Isolation Forest model to {ISO_FOREST_MODEL_PATH}")

    # Step 4: Decision Labeling
    df["deal_status"] = df.apply(assign_case_study_decision, axis=1).astype("category")
    df = df.drop(columns=["is_iso_anomaly"], errors="ignore")

    deal_breakdown = df["deal_status"].value_counts().to_dict()
    logger.info(f"Case Study Decision Breakdown: {deal_breakdown}")

    # Step 5: Export scored dataset with strict 26-column schema
    present_cols = [c for c in FINAL_SCHEMA_COLUMNS if c in df.columns]
    df_export = df[present_cols].copy()
    df_export.to_csv(PROCESSED_SCORED_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Exported {len(df_export)} scored deals (26 cols) to {PROCESSED_SCORED_CSV}!")

    pipeline_summary = {
        "benchmarks": benchmarks,
        "best_metrics": best_metrics,
        "deal_breakdown": deal_breakdown,
        "total_scored_records": len(df_export),
    }
    return df_export, pipeline_summary


if __name__ == "__main__":
    df_scored, summary = run_full_modeling_pipeline()
    print("\n--- MODEL BENCHMARK RESULTS ---")
    for m, met in summary["benchmarks"].items():
        print(f"{m}: {met}")
    print("\n--- DEAL STATUS SUMMARY ---")
    print(summary["deal_breakdown"])
