"""Multi-stage Stratified Crawler for Chợ Tốt Rental Listings.

Overcomes Chợ Tốt's global offset limit (max ~2000 per region) by stratifying queries
across districts (area_v2) for TP. Hồ Chí Minh and Bình Dương.
Outputs raw data in JSON Lines (.jsonl) to preserve nested fields and line-breaks.
"""

import argparse
import datetime
import json
import logging
import random
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

import pandas as pd
from tqdm import tqdm

from src.config import (
    ALL_DISTRICTS,
    CHOTOT_API_ENDPOINT,
    CHOTOT_CATEGORY,
    CHOTOT_DEFAULT_HEADERS,
    CRAWL_METADATA_PATH,
    INTERIM_PARQUET_PATH,
    RAW_JSONL_PATH,
    REGION_BINH_DUONG,
    REGION_HCM,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Crawler")


def fetch_ads_page(
    region_id: int,
    area_id: int,
    offset: int = 0,
    limit: int = 50,
    max_retries: int = 3,
    timeout: int = 10,
) -> Dict[str, Any]:
    """Fetch a single page of listings from Chợ Tốt Gateway API."""
    params = {
        "cg": CHOTOT_CATEGORY,
        "region_v2": region_id,
        "area_v2": area_id,
        "limit": limit,
        "o": offset,
        "st": "u,h",
    }
    url = f"{CHOTOT_API_ENDPOINT}?{urllib.parse.urlencode(params)}"

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=CHOTOT_DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    raw_content = response.read().decode("utf-8", errors="replace")
                    return json.loads(raw_content)
        except Exception as e:
            wait_sec = attempt * 1.5 + random.uniform(0.2, 0.8)
            logger.warning(
                f"Attempt {attempt}/{max_retries} failed for area {area_id} at offset {offset}: {e}. Retrying in {wait_sec:.1f}s..."
            )
            time.sleep(wait_sec)

    logger.error(f"Failed to fetch area {area_id} offset {offset} after {max_retries} retries.")
    return {"ads": [], "total": 0}


def crawl_stratified(
    target_regions: Optional[List[int]] = None,
    max_per_area: Optional[int] = None,
    output_jsonl: Optional[str] = None,
    request_delay: float = 0.35,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Execute multi-stage stratified crawl across districts."""
    if target_regions is None:
        target_regions = [REGION_HCM, REGION_BINH_DUONG]

    out_path = output_jsonl or RAW_JSONL_PATH
    start_time = datetime.datetime.now()
    logger.info(f"Starting stratified crawl for regions {target_regions}. Output: {out_path}")

    total_requests = 0
    total_raw_records = 0
    records_per_district: Dict[str, int] = {}
    seen_ad_ids = set()

    if overwrite and out_path.exists():
        logger.info(f"Overwrite enabled. Removing existing {out_path}...")
        out_path.unlink()

    # If appending or checking prior IDs
    if out_path.exists():
        logger.info("Existing raw file found. Scanning existing ad_ids...")
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            if "ad_id" in record:
                                seen_ad_ids.add(record["ad_id"])
                        except Exception:
                            pass
            logger.info(f"Loaded {len(seen_ad_ids)} previously crawled ad_ids.")
        except Exception as e:
            logger.warning(f"Could not read existing raw file: {e}")

    with open(out_path, "a", encoding="utf-8") as jsonl_file:
        for reg_id in target_regions:
            district_map = ALL_DISTRICTS.get(reg_id, {})
            logger.info(f"=== Crawling Region: {reg_id} with {len(district_map)} districts ===")

            for area_id, district_name in district_map.items():
                offset = 0
                district_records = 0
                logger.info(f"--> District: {district_name} (Code: {area_id})")

                while True:
                    if max_per_area and district_records >= max_per_area:
                        logger.info(f"Reached max limit of {max_per_area} for {district_name}.")
                        break

                    resp = fetch_ads_page(
                        region_id=reg_id,
                        area_id=area_id,
                        offset=offset,
                        limit=50,
                    )
                    total_requests += 1
                    ads = resp.get("ads", [])

                    if not ads:
                        logger.info(f"No more ads for {district_name} (stopped at offset {offset}).")
                        break

                    for ad in ads:
                        if max_per_area and district_records >= max_per_area:
                            break
                        ad_id = ad.get("ad_id")
                        # Add tracking fields
                        ad["_crawled_at"] = datetime.datetime.now().isoformat()
                        ad["_crawl_region_id"] = reg_id
                        ad["_crawl_area_id"] = area_id

                        json_str = json.dumps(ad, ensure_ascii=False)
                        jsonl_file.write(json_str + "\n")
                        jsonl_file.flush()

                        total_raw_records += 1
                        district_records += 1
                        if ad_id:
                            seen_ad_ids.add(ad_id)

                    offset += len(ads)
                    # Polite rate-limiting sleep with jitter
                    time.sleep(request_delay + random.uniform(0.05, 0.15))

                    # If returned less than 50, that was the last page
                    if len(ads) < 50:
                        break

                records_per_district[f"{district_name} ({area_id})"] = district_records
                logger.info(f"Finished {district_name}: Collected {district_records} records.")

    end_time = datetime.datetime.now()
    duration_minutes = (end_time - start_time).total_seconds() / 60.0

    metadata = {
        "crawl_started_at": start_time.isoformat(),
        "crawl_ended_at": end_time.isoformat(),
        "duration_minutes": round(duration_minutes, 2),
        "total_requests": total_requests,
        "total_raw_records_this_run": total_raw_records,
        "unique_ad_ids_total": len(seen_ad_ids),
        "target_regions": target_regions,
        "records_per_district": records_per_district,
    }

    with open(CRAWL_METADATA_PATH, "w", encoding="utf-8") as meta_f:
        json.dump(metadata, meta_f, ensure_ascii=False, indent=2)

    logger.info(
        f"Crawl completed! Total raw records collected this run: {total_raw_records}. Metadata saved to {CRAWL_METADATA_PATH}."
    )
    return metadata


def raw_to_interim(
    raw_jsonl_path: Optional[str] = None,
    output_parquet_path: Optional[str] = None,
) -> pd.DataFrame:
    """Parse raw JSON Lines file into an interim deduplicated Parquet file."""
    in_path = raw_jsonl_path or RAW_JSONL_PATH
    out_path = output_parquet_path or INTERIM_PARQUET_PATH

    if not in_path.exists():
        raise FileNotFoundError(f"Raw data file not found at {in_path}")

    logger.info(f"Parsing raw JSONL {in_path} to interim Parquet...")
    records = []
    with open(in_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue

    logger.info(f"Loaded {len(records)} raw JSON records.")
    df_raw = pd.DataFrame(records)

    # Core key deduplication at interim stage
    if "ad_id" in df_raw.columns:
        initial_len = len(df_raw)
        df_dedup = df_raw.drop_duplicates(subset=["ad_id"], keep="last").copy()
        logger.info(f"Interim deduplication: {initial_len} -> {len(df_dedup)} records ({initial_len - len(df_dedup)} duplicates removed).")
    else:
        df_dedup = df_raw

    # Convert non-scalar / complex columns to strings or drop unneeded internals to allow Parquet storage
    for col in df_dedup.columns:
        if df_dedup[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df_dedup[col] = df_dedup[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x) if pd.notnull(x) else None)

    df_dedup.to_parquet(out_path, index=False)
    logger.info(f"Saved interim deduplicated data ({len(df_dedup)} rows, {len(df_dedup.columns)} cols) to {out_path}.")
    return df_dedup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chợ Tốt Rental Listings Stratified Crawler")
    parser.add_argument(
        "--regions",
        nargs="+",
        type=int,
        default=[REGION_HCM, REGION_BINH_DUONG],
        help="Region IDs to crawl (13000 for HCM, 2011 for Binh Duong)",
    )
    parser.add_argument(
        "--max-per-area",
        type=int,
        default=None,
        help="Maximum listings to fetch per district (None for all)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.35,
        help="Polite request delay in seconds",
    )
    parser.add_argument(
        "--to-interim",
        action="store_true",
        help="Also export to interim Parquet after crawl",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing raw jsonl file instead of appending",
    )
    args = parser.parse_args()

    crawl_stratified(
        target_regions=args.regions,
        max_per_area=args.max_per_area,
        request_delay=args.delay,
        overwrite=args.overwrite,
    )

    if args.to_interim or True:  # Default to converting to interim
        raw_to_interim()

