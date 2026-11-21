"""Feature Engineering Pipeline for IE313 Rental Market Analytics.

Extracts:
1. NLP Regex binary flags (has_mezzanine, has_ac, is_free_curfew, has_balcony_window)
2. Geospatial Haversine distances to Q.1 CBD & VNU-HCM University Village
3. Listing metadata from unused raw API fields (price change, age, images, promo, mặt tiền/hẻm...)
4. area_group (tiny districts merged) for group statistics
5. Behavioral Seller Profiling (Chính chủ, Môi giới công khai, Môi giới trá hình)
6. Member B feature modules (text regex, OSM POI) when present
7. Unsupervised Market Segmentation via K-Means (Tier 1, Tier 2, Tier 3)
8. Exports the full featured dataset to rental_cleaned_full.csv
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
    AREA_GROUP_MIN_SAMPLES,
    AREA_GROUP_OTHER_LABELS,
    BEN_THANH_MARKET,
    PROCESSED_FULL_CSV,
    REGEX_PATTERNS,
    SHARED_DORM_PLACE_EXCLUDE,
    SHARED_DORM_TITLE_PATTERN,
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


def _truthy(series: Optional[pd.Series], index: pd.Index) -> pd.Series:
    """Map mixed bool/str/NaN API flags (True, 'True', 1, '1.0') to 0/1 int8; missing -> 0."""
    if series is None:
        return pd.Series(0, index=index, dtype="int8")
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "1.0"]).astype("int8")


def extract_listing_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Extract listing-level features from raw API fields unused in v1 (dataset v2)."""
    logger.info("Extracting listing metadata features from raw API fields...")
    idx = df.index

    # Location detail: mặt tiền vs hẻm
    df["is_main_street"] = _truthy(df.get("is_main_street"), idx)
    street_no = df.get("street_number", pd.Series("", index=idx)).fillna("").astype(str).str.lower()
    # "23/51", "266/108/33" are alley addresses; also explicit keywords
    df["is_alley"] = street_no.str.contains(r"/|hẻm|hem\b|kiệt|ngõ|ngách", regex=True).astype("int8")

    # Price change since first posting: price_diff = price - original_price (verified on raw data)
    price = pd.to_numeric(df.get("price"), errors="coerce")
    orig_price = pd.to_numeric(df.get("original_price"), errors="coerce")
    valid_orig = orig_price.where(orig_price > 0)
    df["price_change_pct"] = ((price - valid_orig) / valid_orig * 100.0).round(2).fillna(0.0)
    df["has_price_change"] = (df["price_change_pct"].abs() > 0).astype("int8")

    # Listing age: last refresh time minus original posting time (days)
    orig_time = pd.to_datetime(pd.to_numeric(df.get("orig_list_time"), errors="coerce"), unit="ms", errors="coerce")
    age = (pd.to_datetime(df["list_time"]) - orig_time).dt.total_seconds() / 86400.0
    df["listing_age_days"] = age.where(age >= 0).round(2)

    # Listing quality / effort signals
    df["n_images"] = pd.to_numeric(df.get("number_of_images"), errors="coerce").fillna(0).astype("int16")
    df["has_video"] = _truthy(df.get("has_video"), idx)
    df["is_paid_promo"] = (
        _truthy(df.get("is_sticky"), idx)
        | _truthy(df.get("special_display"), idx)
        | df.get("stickyad_feature", pd.Series(index=idx, dtype=object)).notna().astype("int8")
    ).astype("int8")
    shop = df.get("shop", pd.Series(index=idx, dtype=object))
    df["has_shop"] = (shop.notna() & ~shop.astype(str).isin(["", "None", "nan"])).astype("int8")
    df["seller_rating"] = pd.to_numeric(df.get("average_rating_for_seller"), errors="coerce")
    df["seller_n_ratings"] = pd.to_numeric(df.get("total_rating_for_seller"), errors="coerce").fillna(0).astype("int32")
    df["body_length"] = df.get("body", pd.Series("", index=idx)).fillna("").astype(str).str.len().astype("int32")

    logger.info(
        "Metadata: main_street=%.1f%% | alley=%.1f%% | price_changed=%.1f%% | paid_promo=%.1f%% | video=%.1f%%",
        df["is_main_street"].mean() * 100, df["is_alley"].mean() * 100,
        df["has_price_change"].mean() * 100, df["is_paid_promo"].mean() * 100, df["has_video"].mean() * 100,
    )
    return df


def flag_shared_dorm(df: pd.DataFrame) -> pd.DataFrame:
    """Flag KTX / sleepbox / ở ghép listings (price per bed/person) from the title."""
    title = df.get("subject", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    title = title.str.replace(SHARED_DORM_PLACE_EXCLUDE, " ", regex=True)
    df["is_shared_or_dorm"] = title.str.contains(SHARED_DORM_TITLE_PATTERN, regex=True).astype("int8")
    logger.info(
        f"Shared/dorm (giá theo giường) listings: {int(df['is_shared_or_dorm'].sum())} "
        f"({df['is_shared_or_dorm'].mean() * 100:.1f}%) -> excluded from room fair-price model"
    )
    return df


def compute_area_group(df: pd.DataFrame) -> pd.DataFrame:
    """Merge districts with too few listings into a regional 'other' bucket (area_name is kept intact)."""
    counts = df["area_name"].value_counts()
    small = set(counts[counts < AREA_GROUP_MIN_SAMPLES].index)
    other_label = df["region_name"].astype(str).map(AREA_GROUP_OTHER_LABELS).fillna("Khác")
    df["area_group"] = np.where(df["area_name"].isin(small), other_label, df["area_name"].astype(str))
    logger.info(f"area_group: merged {len(small)} small districts (<{AREA_GROUP_MIN_SAMPLES} listings): {sorted(small)}")
    return df


def apply_member_b_features(df: pd.DataFrame) -> pd.DataFrame:
    """Plug in member B's feature modules when they exist (see reports/BAN_GIAO_THANH_VIEN_B.md).

    - src/text_features.py      -> add_text_features(df)   (extended NLP regex)
    - src/external_features.py  -> add_poi_features(df)    (OpenStreetMap POI distances)
    Missing modules are skipped so the pipeline always runs.
    """
    try:
        from src.text_features import add_text_features
        df = add_text_features(df)
        logger.info("Applied src.text_features.add_text_features")
    except ImportError:
        logger.info("src.text_features not available yet -> skipped")
    try:
        from src.external_features import add_poi_features
        df = add_poi_features(df)
        logger.info("Applied src.external_features.add_poi_features")
    except ImportError:
        logger.info("src.external_features not available yet -> skipped")
    return df


def classify_seller_type(df: pd.DataFrame) -> pd.DataFrame:
    """Classify listing posters into Chính chủ, Môi giới công khai, or Môi giới trá hình.

    - Môi giới công khai: API flag company_ad = True (người đăng tự khai là môi giới trên Chợ Tốt).
    - Môi giới trá hình: tự khai cá nhân nhưng đăng >= 4 tin, HOẶC đăng ở >= 2 quận/huyện khác nhau
      (chủ trọ thật hiếm khi có phòng ở nhiều quận). Vì mẫu bị giới hạn 140-300 tin/quận nên
      số tin đếm được là cận dưới -> nhóm này nhỏ, chỉ dùng mô tả, không dùng để kiểm định.
    - Chính chủ: còn lại.
    """
    logger.info("Profiling seller behavior based on account posting frequency...")

    account_counts = df["account_id"].value_counts().to_dict()
    df["account_ad_count"] = df["account_id"].map(account_counts).fillna(1).astype("int32")
    df["account_n_areas"] = df.groupby("account_id")["area_name"].transform("nunique").astype("int16")

    # Check company_ad flag from API
    company_flag = df.get("company_ad", False)
    if isinstance(company_flag, pd.Series):
        is_company = company_flag.astype(str).str.lower().isin(["true", "1"])
    else:
        is_company = pd.Series([False] * len(df), index=df.index)

    def determine_seller(row):
        if row["is_company"]:
            return "Môi giới công khai"
        elif row["account_ad_count"] >= 4 or row["account_n_areas"] >= 2:
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
    df = extract_listing_metadata(df)
    df = flag_shared_dorm(df)
    df = compute_area_group(df)
    df = classify_seller_type(df)
    df = apply_member_b_features(df)
    df = cluster_market_tiers(df)

    # Reorder / format categorical types
    for cat_col in ["region_name", "area_name", "area_group", "ward_name", "furnishing_status", "seller_type", "market_cluster"]:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype("category")

    # Export to processed full CSV
    df.to_csv(PROCESSED_FULL_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Saved full cleaned & featured dataset ({len(df)} rows) to {PROCESSED_FULL_CSV}.")
    return df


if __name__ == "__main__":
    df_feat = build_feature_pipeline()
    logger.info(f"Feature engineering pipeline completed successfully! Output rows: {len(df_feat)}")

