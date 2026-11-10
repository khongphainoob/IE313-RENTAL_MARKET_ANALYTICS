"""Statistical Hypothesis Testing Suite for Rental Market Analytics.

Implements non-parametric statistical tests (suited for right-skewed real estate pricing):
1. Mann-Whitney U Test (Binary amenities vs. Price / Price per m2)
2. Kruskal-Wallis H Test (Non-parametric multi-group ANOVA for Districts, Sellers, Tiers)
3. Spearman Rank Correlation (Geospatial distances & Area vs. Rent)
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.config import PROCESSED_FULL_CSV

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("StatsTests")


def run_mann_whitney_u(
    df: pd.DataFrame,
    binary_col: str,
    target_col: str = "price_million",
) -> Dict[str, Any]:
    """Perform Mann-Whitney U test comparing target distribution between 0 and 1 groups."""
    g0 = df[df[binary_col] == 0][target_col].dropna()
    g1 = df[df[binary_col] == 1][target_col].dropna()

    n0, n1 = len(g0), len(g1)
    if n0 == 0 or n1 == 0:
        return {
            "feature": binary_col,
            "target": target_col,
            "error": "One or both groups have 0 samples",
        }

    stat, p_val = stats.mannwhitneyu(g1, g0, alternative="two-sided")
    # Rank-biserial correlation effect size: r = 1 - (2U / (n1 * n2))
    u_val = stat
    effect_size_r = 1.0 - (2.0 * u_val / (n0 * n1))

    med0, med1 = g0.median(), g1.median()
    mean0, mean1 = g0.mean(), g1.mean()
    premium_pct = ((med1 - med0) / med0 * 100) if med0 > 0 else 0.0

    return {
        "feature": binary_col,
        "target": target_col,
        "n_group_0": n0,
        "n_group_1": n1,
        "median_0": round(med0, 2),
        "median_1": round(med1, 2),
        "mean_0": round(mean0, 2),
        "mean_1": round(mean1, 2),
        "median_diff_pct": round(premium_pct, 1),
        "u_statistic": round(stat, 2),
        "p_value": p_val,
        "is_significant_005": p_val < 0.05,
        "is_significant_001": p_val < 0.001,
        "effect_size_r": round(effect_size_r, 3),
    }


def run_kruskal_wallis(
    df: pd.DataFrame,
    group_col: str,
    target_col: str = "price_per_m2_k",
    min_samples_per_group: int = 10,
) -> Dict[str, Any]:
    """Perform Kruskal-Wallis H test across multiple groups."""
    grouped = df.groupby(group_col)[target_col].apply(lambda s: s.dropna().tolist())
    valid_groups = {k: v for k, v in grouped.items() if len(v) >= min_samples_per_group}

    if len(valid_groups) < 2:
        return {
            "group_feature": group_col,
            "target": target_col,
            "error": f"Fewer than 2 groups met the sample size threshold ({min_samples_per_group})",
        }

    group_arrays = list(valid_groups.values())
    h_stat, p_val = stats.kruskal(*group_arrays)

    # Eta-squared effect size for Kruskal-Wallis: eta2 = (H - k + 1) / (N - k)
    N = sum(len(v) for v in group_arrays)
    k = len(group_arrays)
    eta_squared = (h_stat - k + 1) / (N - k) if N > k else 0.0

    group_medians = {k: round(np.median(v), 2) for k, v in valid_groups.items()}

    return {
        "group_feature": group_col,
        "target": target_col,
        "num_groups": k,
        "total_samples": N,
        "h_statistic": round(h_stat, 2),
        "p_value": p_val,
        "is_significant_005": p_val < 0.05,
        "eta_squared": round(max(0.0, eta_squared), 4),
        "group_medians": group_medians,
    }


def run_spearman_correlations(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    target_col: str = "price_million",
) -> pd.DataFrame:
    """Compute Spearman rank correlations and p-values for continuous features."""
    if feature_cols is None:
        feature_cols = [
            "size_m2",
            "dist_to_q1_km",
            "dist_to_vnuhcm_km",
            "deposit_million",
            "price_per_m2_k",
        ]

    results = []
    for col in feature_cols:
        if col not in df.columns:
            continue
        valid = df[[col, target_col]].dropna()
        if len(valid) < 5:
            continue
        rho, p_val = stats.spearmanr(valid[col], valid[target_col])
        results.append({
            "feature": col,
            "target": target_col,
            "spearman_rho": round(rho, 4),
            "p_value": p_val,
            "is_significant_005": p_val < 0.05,
            "sample_size": len(valid),
        })

    return pd.DataFrame(results)


def run_all_hypothesis_tests(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Run comprehensive hypothesis testing suite for all key research questions."""
    if df is None:
        if not PROCESSED_FULL_CSV.exists():
            raise FileNotFoundError(f"{PROCESSED_FULL_CSV} not found. Run pipeline first.")
        df = pd.read_csv(PROCESSED_FULL_CSV)

    logger.info("=== Running Mann-Whitney U Tests on Amenities ===")
    amenity_cols = ["has_mezzanine", "has_ac", "is_free_curfew", "has_balcony_window"]
    amenity_results = []
    for am in amenity_cols:
        if am in df.columns:
            res_price = run_mann_whitney_u(df, am, "price_million")
            res_m2 = run_mann_whitney_u(df, am, "price_per_m2_k")
            amenity_results.append({
                "Amenity": am,
                "Rent Premium (%)": res_price.get("median_diff_pct"),
                "p-value (Price)": res_price.get("p_value"),
                "Price Effect Size (r)": res_price.get("effect_size_r"),
                "p-value (Price/m²)": res_m2.get("p_value"),
            })
    df_amenities = pd.DataFrame(amenity_results)

    logger.info("=== Running Kruskal-Wallis Tests on Categoricals ===")
    kw_district = run_kruskal_wallis(df, "area_name", "price_per_m2_k")
    kw_seller = run_kruskal_wallis(df, "seller_type", "price_per_m2_k")
    kw_cluster = run_kruskal_wallis(df, "market_cluster", "price_million")

    logger.info("=== Running Spearman Correlation on Geospatial & Size ===")
    df_spearman = run_spearman_correlations(df)

    summary = {
        "amenity_tests": df_amenities,
        "kruskal_district": kw_district,
        "kruskal_seller": kw_seller,
        "kruskal_cluster": kw_cluster,
        "spearman_correlations": df_spearman,
    }
    return summary


if __name__ == "__main__":
    tests = run_all_hypothesis_tests()
    print("\n--- AMENITY IMPACT (Mann-Whitney U) ---")
    print(tests["amenity_tests"].to_string())
    print("\n--- SPEARMAN CORRELATIONS ---")
    print(tests["spearman_correlations"].to_string())
