"""Data Cleaning Pipeline (5-Tier Academic Standard).

Implements:
1. Dual-layer Deduplication (ad_id + broker multi-post spam)
2. Domain Sanity Filtering (Price: [0.5, 25.0] mil, Size: [5.0, 120.0] m2)
3. Grouped IQR Outlier Removal by District (area_name) on price_per_m2_k
4. Missing Data Imputation (Deposit via district ratio, Coordinates via Ward centroid)
5. Audit Tracking (Data Funnel metrics saved to data_audit_report.json)
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import (
    AUDIT_REPORT_PATH,
    INTERIM_PARQUET_PATH,
    PRICE_MAX_MILLION,
    PRICE_MIN_MILLION,
    PROCESSED_FULL_CSV,
    RAW_JSONL_PATH,
    SIZE_MAX_M2,
    SIZE_MIN_M2,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Cleaner")


def load_raw_or_interim() -> pd.DataFrame:
    """Load data from interim parquet or raw jsonl fallback."""
    if INTERIM_PARQUET_PATH.exists():
        logger.info(f"Loading interim data from {INTERIM_PARQUET_PATH}...")
        df = pd.read_parquet(INTERIM_PARQUET_PATH)
    elif RAW_JSONL_PATH.exists():
        logger.info(f"Loading raw jsonl from {RAW_JSONL_PATH}...")
        records = []
        with open(RAW_JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
        df = pd.DataFrame(records)
    else:
        raise FileNotFoundError("Neither interim parquet nor raw jsonl found. Run crawler first.")
    return df


def clean_rental_dataset(df_input: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Execute complete 5-tier academic cleaning pipeline."""
    df = df_input.copy() if df_input is not None else load_raw_or_interim()
    initial_count = len(df)
    audit: Dict[str, Any] = {
        "step_0_raw_records": initial_count,
        "funnel_steps": [],
    }

    def record_step(name: str, count: int, desc: str):
        audit["funnel_steps"].append({
            "step": name,
            "count": count,
            "dropped": (audit["funnel_steps"][-1]["count"] - count) if audit["funnel_steps"] else 0,
            "retention_pct": round((count / initial_count) * 100, 2) if initial_count else 0,
            "description": desc,
        })
        logger.info(f"[{name}] Remaining: {count} listings | Description: {desc}")

    record_step("0_RawInput", initial_count, "Dữ liệu thô ban đầu thu thập từ API Chợ Tốt")

    # ==========================================
    # TIER 1: DUAL-LAYER DEDUPLICATION
    # ==========================================
    # 1a. Dedup by primary key ad_id
    if "ad_id" in df.columns:
        df["ad_id"] = pd.to_numeric(df["ad_id"], errors="coerce")
        df = df.dropna(subset=["ad_id"])
        df["ad_id"] = df["ad_id"].astype("int64")
        df = df.drop_duplicates(subset=["ad_id"], keep="last")
    record_step("1a_DedupAdId", len(df), "Khử trùng lặp khóa chính ad_id")

    # Standardize basic columns needed for broker dedup
    # Price standardizing (API returns price in VND, e.g., 3500000 -> 3.5 million)
    df["price_raw"] = pd.to_numeric(df.get("price"), errors="coerce")
    df["price_million"] = df["price_raw"] / 1_000_000.0

    # Size standardizing (API returns size in m2)
    df["size_m2"] = pd.to_numeric(df.get("size"), errors="coerce")

    # Ward and Account
    df["account_id"] = pd.to_numeric(df.get("account_id"), errors="coerce").fillna(-1).astype("int64")
    df["ward_name"] = df.get("ward_name", "").astype(str).str.strip()
    df["area_name"] = df.get("area_name", "").astype(str).str.strip()
    df["region_name"] = df.get("region_name", "").astype(str).str.strip()

    # 1b. Broker spam deduplication: multiple ads with same (account_id, ward_name, size, price)
    df = df.drop_duplicates(
        subset=["account_id", "ward_name", "size_m2", "price_million"],
        keep="first",
    )
    record_step("1b_DedupBrokerSpam", len(df), "Khử trùng lặp spam môi giới cùng phòng đăng nhiều lần")

    # ==========================================
    # TIER 2: DOMAIN SANITY FILTERING
    # ==========================================
    sanity_mask = (
        (df["price_million"] >= PRICE_MIN_MILLION)
        & (df["price_million"] <= PRICE_MAX_MILLION)
        & (df["size_m2"] >= SIZE_MIN_M2)
        & (df["size_m2"] <= SIZE_MAX_M2)
    )
    df = df[sanity_mask].copy()
    record_step("2_DomainSanity", len(df), f"Lọc miền hợp lệ: Giá [{PRICE_MIN_MILLION}, {PRICE_MAX_MILLION}] tr, Diện tích [{SIZE_MIN_M2}, {SIZE_MAX_M2}] m²")

    # Unit price calculation: thousand VND per m2
    df["price_per_m2_k"] = (df["price_million"] * 1000.0) / df["size_m2"]

    # ==========================================
    # TIER 3: GROUPED IQR OUTLIER FILTERING BY DISTRICT
    # ==========================================
    # Compute IQR per area_name to respect local market pricing
    valid_indices = []
    global_q1 = df["price_per_m2_k"].quantile(0.25)
    global_q3 = df["price_per_m2_k"].quantile(0.75)
    global_iqr = global_q3 - global_q1
    global_lower = max(0.0, global_q1 - 1.5 * global_iqr)
    global_upper = global_q3 + 1.5 * global_iqr

    for area, group in df.groupby("area_name"):
        if len(group) >= 15:
            q1 = group["price_per_m2_k"].quantile(0.25)
            q3 = group["price_per_m2_k"].quantile(0.75)
            iqr = q3 - q1
            lower_bound = max(0.0, q1 - 1.5 * iqr)
            upper_bound = q3 + 1.5 * iqr
        else:
            lower_bound = global_lower
            upper_bound = global_upper

        inlier_mask = (group["price_per_m2_k"] >= lower_bound) & (group["price_per_m2_k"] <= upper_bound)
        valid_indices.extend(group[inlier_mask].index.tolist())

    df = df.loc[valid_indices].copy()
    record_step("3_GroupedIQROutliers", len(df), "Lọc ngoại lai đơn giá (price_per_m2_k) theo phương pháp Grouped IQR từng Quận")

    # ==========================================
    # TIER 4: MISSING DATA IMPUTATION
    # ==========================================
    # 4a. Deposit imputation
    # Standardize deposit
    df["deposit_raw"] = pd.to_numeric(df.get("deposit"), errors="coerce")
    df["deposit_million"] = df["deposit_raw"] / 1_000_000.0

    # Calculate median ratio of deposit / price per district
    valid_deposit_mask = (df["deposit_million"] > 0) & (df["deposit_million"] <= df["price_million"] * 3.0)
    df_valid_dep = df[valid_deposit_mask].copy()
    df_valid_dep["dep_ratio"] = df_valid_dep["deposit_million"] / df_valid_dep["price_million"]

    district_dep_ratios = df_valid_dep.groupby("area_name")["dep_ratio"].median().to_dict()
    global_median_ratio = df_valid_dep["dep_ratio"].median() if not df_valid_dep.empty else 1.0

    # Impute missing or invalid deposit
    def fill_deposit(row):
        val = row["deposit_million"]
        if pd.isna(val) or val <= 0 or val > row["price_million"] * 3.0:
            ratio = district_dep_ratios.get(row["area_name"], global_median_ratio)
            return round(row["price_million"] * ratio, 2)
        return round(val, 2)

    df["deposit_million"] = df.apply(fill_deposit, axis=1)

    # 4b. Geospatial coordinates imputation (Median Centroid by Ward / Area)
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")

    # Southern Vietnam bounding box roughly: Lat [10.3, 11.6], Lon [106.2, 107.2]
    coord_valid_mask = (
        (df["latitude"] >= 10.3)
        & (df["latitude"] <= 11.6)
        & (df["longitude"] >= 106.2)
        & (df["longitude"] <= 107.2)
    )

    # Compute centroids by Ward
    ward_centroids = (
        df[coord_valid_mask]
        .groupby(["area_name", "ward_name"])[["latitude", "longitude"]]
        .median()
        .to_dict(orient="index")
    )
    area_centroids = (
        df[coord_valid_mask]
        .groupby("area_name")[["latitude", "longitude"]]
        .median()
        .to_dict(orient="index")
    )

    # Global fallback (District 1 centroid)
    global_lat, global_lon = 10.7769, 106.7009

    def fill_coordinates(row):
        lat = row["latitude"]
        lon = row["longitude"]
        if not (10.3 <= lat <= 11.6 and 106.2 <= lon <= 107.2) or pd.isna(lat) or pd.isna(lon):
            key_ward = (row["area_name"], row["ward_name"])
            if key_ward in ward_centroids and not pd.isna(ward_centroids[key_ward]["latitude"]):
                return ward_centroids[key_ward]["latitude"], ward_centroids[key_ward]["longitude"]
            key_area = row["area_name"]
            if key_area in area_centroids and not pd.isna(area_centroids[key_area]["latitude"]):
                return area_centroids[key_area]["latitude"], area_centroids[key_area]["longitude"]
            return global_lat, global_lon
        return lat, lon

    coords = df.apply(fill_coordinates, axis=1)
    df["latitude"] = [c[0] for c in coords]
    df["longitude"] = [c[1] for c in coords]

    # Additional standardizations
    df["list_id"] = pd.to_numeric(df.get("list_id"), errors="coerce").fillna(df["ad_id"]).astype("int64")

    # Datetime conversion from list_time ms
    if "list_time" in df.columns:
        df["list_time"] = pd.to_datetime(df["list_time"], unit="ms", errors="coerce").fillna(pd.Timestamp.now())
    else:
        df["list_time"] = pd.Timestamp.now()

    # Street name
    df["street_name"] = df.get("street_name", "").fillna("Đang cập nhật").astype(str).str.strip()
    df["street_name"] = df["street_name"].replace({"": "Đang cập nhật", "nan": "Đang cập nhật"})

    # Furnishing status
    # In Chợ Tốt API: furnishing_rent 1: Đầy đủ, 2: Cao cấp/Cơ bản, etc.
    furnish_map = {
        1: "Đầy đủ",
        2: "Cơ bản",
        3: "Nhà trống",
    }
    df["furnishing_status"] = df.get("furnishing_rent").map(furnish_map).fillna("Không rõ")

    record_step("4_MissingImputed", len(df), "Điền khuyết tiền cọc (theo tỷ lệ Quận) và tọa độ địa lý (theo tâm Phường)")

    # Save audit report
    with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    logger.info(f"Audit report saved to {AUDIT_REPORT_PATH}")

    return df, audit


if __name__ == "__main__":
    df_cleaned, report = clean_rental_dataset()
    logger.info(f"Cleaner pipeline completed successfully! Cleaned records: {len(df_cleaned)}")
