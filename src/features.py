"""Feature Engineering Pipeline for IE313 Rental Market Analytics.

Extracts:
1. NLP Regex binary flags (has_mezzanine, has_ac, is_free_curfew, has_balcony_window)
2. Geospatial Haversine distances to Q.1 CBD & VNU-HCM University Village
3. Behavioral Seller Profiling (Chính chủ, Môi giới công khai, Môi giới trá hình)
4. Unsupervised Market Segmentation via K-Means (Tier 1, Tier 2, Tier 3)
5. Exports complete 26-column standard dataset to rental_cleaned_full.csv
"""

import logging
import re
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.cleaner import clean_rental_dataset
from src.config import (
    BEN_THANH_MARKET,
    PROCESSED_FULL_CSV,
    REGEX_PATTERNS,
    VNU_HCM,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Features")


def haversine_distance(
    lat1: np.ndarray,
    lon1: np.ndarray,
    lat2: float,
    lon2: float,
) -> np.ndarray:
    """Calculate Haversine great-circle distance between coordinate arrays and a fixed landmark in km."""
    R = 6371.0  # Earth radius in kilometers

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = (
        np.sin(delta_phi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return np.round(R * c, 2)


def extract_regex_amenities(df: pd.DataFrame) -> pd.DataFrame:
    """Extract binary 0/1 amenity flags from listing title and description."""
    logger.info("Extracting NLP regex amenity features from title and body...")

    # Combine subject (title) and body (description)
    text_corpus = (
        df.get("subject", "").fillna("").astype(str)
        + " "
        + df.get("body", "").fillna("").astype(str)
    ).str.lower()

    for col_name, pattern in REGEX_PATTERNS.items():
        compiled_regex = re.compile(pattern, re.IGNORECASE)
        df[col_name] = text_corpus.apply(
            lambda t: 1 if compiled_regex.search(t) else 0
        ).astype("int8")
        positive_count = df[col_name].sum()
        pct = (positive_count / len(df)) * 100 if len(df) else 0
        logger.info(f"Feature [{col_name}]: {positive_count} listings ({pct:.1f}%) positive.")

    return df


def compute_geospatial_distances(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Haversine distances to Ben Thanh (Q1) and VNU-HCM."""
    logger.info("Calculating Haversine geospatial distances...")

    lats = df["latitude"].values
    lons = df["longitude"].values

    df["dist_to_q1_km"] = haversine_distance(
        lats, lons, BEN_THANH_MARKET["lat"], BEN_THANH_MARKET["lon"]
    )
    df["dist_to_vnuhcm_km"] = haversine_distance(
        lats, lons, VNU_HCM["lat"], VNU_HCM["lon"]
    )

    logger.info(
        f"Mean dist to Q1: {df['dist_to_q1_km'].mean():.2f} km | Mean dist to VNU-HCM: {df['dist_to_vnuhcm_km'].mean():.2f} km"
    )
    return df


def classify_seller_type(df: pd.DataFrame) -> pd.DataFrame:
    """Classify listing posters into Chính chủ, Môi giới công khai, or Môi giới trá hình."""
    logger.info("Profiling seller behavior based on account posting frequency...")

    account_counts = df["account_id"].value_counts().to_dict()
    df["account_ad_count"] = df["account_id"].map(account_counts).fillna(1)

    # Check company_ad flag from API
    company_flag = df.get("company_ad", False)
    if isinstance(company_flag, pd.Series):
        is_company = company_flag.astype(str).str.lower().isin(["true", "1"])
    else:
        is_company = pd.Series([False] * len(df), index=df.index)

    def determine_seller(row):
        if row["is_company"]:
            return "Môi giới công khai"
        elif row["account_ad_count"] >= 4:
            return "Môi giới trá hình"
        else:
            return "Chính chủ"

    df["is_company"] = is_company
    df["seller_type"] = df.apply(determine_seller, axis=1).astype("category")

    seller_dist = df["seller_type"].value_counts().to_dict()
    logger.info(f"Seller distribution: {seller_dist}")
    return df


def cluster_market_tiers(df: pd.DataFrame, n_clusters: int = 3) -> pd.DataFrame:
    """Segment rental market into tiers using K-Means clustering."""
    logger.info(f"Clustering listings into {n_clusters} market segments using K-Means...")

    feature_cols = [
        "price_million",
        "size_m2",
        "price_per_m2_k",
        "has_ac",
        "has_mezzanine",
        "dist_to_q1_km",
    ]
    X = df[feature_cols].copy().fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    raw_clusters = kmeans.fit_predict(X_scaled)
    df["_cluster_raw"] = raw_clusters

    # Map raw cluster IDs so that ordering reflects median price per m2
    cluster_order = (
        df.groupby("_cluster_raw")["price_per_m2_k"]
        .median()
        .sort_values()
        .index.tolist()
    )

    tier_labels = [
        "Tier 1: Sinh viên/Bình dân",
        "Tier 2: Tiện nghi tầm trung",
        "Tier 3: Studio/Căn hộ dịch vụ",
    ]
    cluster_map = {old_id: tier_labels[rank] for rank, old_id in enumerate(cluster_order)}
    df["market_cluster"] = df["_cluster_raw"].map(cluster_map).astype("category")
    df = df.drop(columns=["_cluster_raw"])

    logger.info("Market Cluster Breakdown:\n" + str(df["market_cluster"].value_counts()))
    return df


def build_feature_pipeline(df_cleaned: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Run full feature engineering pipeline and export rental_cleaned_full.csv."""
    if df_cleaned is None:
        df_cleaned, _ = clean_rental_dataset()

    df = df_cleaned.copy()
    df = extract_regex_amenities(df)
    df = compute_geospatial_distances(df)
    df = classify_seller_type(df)
    df = cluster_market_tiers(df)

    # Reorder / format categorical types
    for cat_col in ["region_name", "area_name", "ward_name", "furnishing_status", "seller_type", "market_cluster"]:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype("category")

    # Export to processed full CSV
    df.to_csv(PROCESSED_FULL_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Saved full cleaned & featured dataset ({len(df)} rows) to {PROCESSED_FULL_CSV}.")
    return df


if __name__ == "__main__":
    df_feat = build_feature_pipeline()
    logger.info(f"Feature engineering pipeline completed successfully! Output rows: {len(df_feat)}")

