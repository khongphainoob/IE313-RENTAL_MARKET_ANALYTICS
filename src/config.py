"""Configuration module for IE313 Rental Market Analytics.

Defines filesystem paths, API endpoints, district maps, geospatial coordinates,
domain filtering thresholds, and regex patterns for feature engineering.
"""

from pathlib import Path

# ==========================================
# 1. DIRECTORY & FILE PATHS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_INTERIM_DIR = DATA_DIR / "interim"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DASHBOARD_DIR = BASE_DIR / "dashboard"

# Ensure all directories exist
for folder in [DATA_RAW_DIR, DATA_INTERIM_DIR, DATA_PROCESSED_DIR, MODELS_DIR, FIGURES_DIR, DASHBOARD_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# File paths
RAW_JSONL_PATH = DATA_RAW_DIR / "chotot_raw_hcm_bd.jsonl"
CRAWL_METADATA_PATH = DATA_RAW_DIR / "crawl_metadata.json"
INTERIM_PARQUET_PATH = DATA_INTERIM_DIR / "deduplicated_data.parquet"
PROCESSED_FULL_CSV = DATA_PROCESSED_DIR / "rental_cleaned_full.csv"
PROCESSED_SCORED_CSV = DATA_PROCESSED_DIR / "rental_scored_deals.csv"
AUDIT_REPORT_PATH = DATA_PROCESSED_DIR / "data_audit_report.json"

LGBM_MODEL_PATH = MODELS_DIR / "lgbm_fair_price.joblib"
ISO_FOREST_MODEL_PATH = MODELS_DIR / "iso_forest_anomaly.joblib"

# ==========================================
# 2. CHOTOT API CONFIGURATION
# ==========================================
CHOTOT_API_ENDPOINT = "https://gateway.chotot.com/v1/public/ad-listing"
CHOTOT_CATEGORY = 1050  # Phòng trọ, nhà trọ

CHOTOT_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

# ==========================================
# 3. REGION & DISTRICT MAPPING
# ==========================================
REGION_HCM = 13000
REGION_BINH_DUONG = 2011

REGIONS = {
    REGION_HCM: "TP. Hồ Chí Minh",
    REGION_BINH_DUONG: "Bình Dương",
}

# District code mapping for TP. Hồ Chí Minh (22 administrative units)
HCM_DISTRICTS = {
    13096: "Quận 1",
    13098: "Quận 3",
    13099: "Quận 4",
    13100: "Quận 5",
    13101: "Quận 6",
    13102: "Quận 7",
    13103: "Quận 8",
    13105: "Quận 10",
    13106: "Quận 11",
    13107: "Quận 12",
    13108: "Quận Bình Tân",
    13109: "Quận Bình Thạnh",
    13110: "Quận Gò Vấp",
    13111: "Quận Phú Nhuận",
    13112: "Quận Tân Bình",
    13113: "Quận Tân Phú",
    13115: "Huyện Bình Chánh",
    13116: "Huyện Củ Chi",
    13117: "Huyện Hóc Môn",
    13118: "Huyện Nhà Bè",
    13119: "Thành phố Thủ Đức",
    13120: "Huyện Cần Giờ",
}

# District code mapping for Bình Dương
BD_DISTRICTS = {
    201101: "Thành phố Thủ Dầu Một",
    201102: "Huyện Bàu Bàng",
    201103: "Huyện Dầu Tiếng",
    201104: "Thị xã Bến Cát",
    201106: "Thị xã Tân Uyên",
    201107: "Thành phố Dĩ An",
    201108: "Thành phố Thuận An",
    201109: "Huyện Bắc Tân Uyên",
}

ALL_DISTRICTS = {
    REGION_HCM: HCM_DISTRICTS,
    REGION_BINH_DUONG: BD_DISTRICTS,
}

# ==========================================
# 4. GEOSPATIAL REFERENCE LANDMARKS
# ==========================================
# Central Business District (Q.1) - Ben Thanh Market
BEN_THANH_MARKET = {
    "name": "Chợ Bến Thành, Quận 1",
    "lat": 10.7725,
    "lon": 106.6980,
}

# Academic & Tech Hub - VNU-HCM University Village
VNU_HCM = {
    "name": "Khu Đô thị ĐHQG-HCM (Làng Đại học)",
    "lat": 10.8756,
    "lon": 106.8007,
}

# ==========================================
# 5. DOMAIN SANITY THRESHOLDS
# ==========================================
PRICE_MIN_MILLION = 0.5    # 500,000 VND / month
PRICE_MAX_MILLION = 25.0   # 25,000,000 VND / month
SIZE_MIN_M2 = 5.0          # 5 m2
SIZE_MAX_M2 = 120.0        # 120 m2

# ==========================================
# 6. NLP REGEX FEATURE EXTRACTION PATTERNS
# ==========================================
REGEX_PATTERNS = {
    "has_mezzanine": r"(gác\s*(lửng|cao|đúc|xép|gỗ)?|có gác|lửng|tầng lửng)",
    "has_ac": r"(máy lạnh|điều h[oò]a|air\s*con|ac\b|máy điều hòa)",
    "is_free_curfew": r"(giờ\s*(giấc)?\s*tự\s*do|không chung chủ|k\s*chung chủ|riêng biệt|khoá vân tay|khóa vân tay|cửa vân tay|tự do ra vào)",
    "has_balcony_window": r"(ban công|cửa sổ|thoáng mát|view|ánh sáng|logia)",
}

# ==========================================
# 7. SCHEMA DEFINITIONS (26-COLUMN STANDARD)
# ==========================================
FINAL_SCHEMA_COLUMNS = [
    "ad_id",
    "list_id",
    "account_id",
    "list_time",
    "region_name",
    "area_name",
    "ward_name",
    "street_name",
    "longitude",
    "latitude",
    "size_m2",
    "price_million",
    "price_per_m2_k",
    "deposit_million",
    "furnishing_status",
    "has_mezzanine",
    "has_ac",
    "is_free_curfew",
    "has_balcony_window",
    "dist_to_q1_km",
    "dist_to_vnuhcm_km",
    "seller_type",
    "market_cluster",
    "predicted_price",
    "valuation_gap_pct",
    "deal_status",
]
