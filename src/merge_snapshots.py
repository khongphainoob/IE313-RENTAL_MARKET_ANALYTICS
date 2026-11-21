"""Merge every crawl (baseline 10/11 + daily snapshots) into ONE deduplicated raw dataset.

Sources (oldest -> newest):
    data/raw/chotot_raw_hcm_bd.jsonl            baseline crawl (10/11/2026, 140 tin/quận)
    data/raw/snapshots/YYYY-MM-DD.jsonl.gz      daily snapshots (300 tin/quận)

For each ad_id the MOST RECENT version is kept (current price/status), plus tracking columns:
    _first_seen        first crawl date the ad appeared in
    _last_seen         last crawl date the ad appeared in
    _n_seen            number of crawls the ad appeared in
    _price_first_seen  price (VND) when first seen -> compare with `price` for price changes

Outputs (data/raw/merged/):
    chotot_merged_raw.jsonl.gz   full fidelity (all API fields, nested JSON kept)
    chotot_merged_raw.csv        flat, utf-8-sig, with ad_url (Excel / Power BI)
    chotot_merged_raw.xlsx       same as CSV for quick viewing
    merge_metadata.json          per-source counts
and data/interim/deduplicated_data.parquet, which src.cleaner reads -> the whole pipeline
(cleaner -> features -> models) runs on the merged dataset.

Re-run any time new snapshots arrive:
    python -m src.merge_snapshots
"""

import datetime
import gzip
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import pandas as pd

from src.config import DATA_RAW_DIR, INTERIM_PARQUET_PATH, RAW_JSONL_PATH, SNAPSHOT_DIR

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("Merge")

MERGED_DIR = DATA_RAW_DIR / "merged"
MERGED_JSONL_GZ = MERGED_DIR / "chotot_merged_raw.jsonl.gz"
MERGED_CSV = MERGED_DIR / "chotot_merged_raw.csv"
MERGED_XLSX = MERGED_DIR / "chotot_merged_raw.xlsx"
MERGED_META = MERGED_DIR / "merge_metadata.json"

PRIORITY_COLS = [
    "ad_id", "list_id", "ad_url", "_first_seen", "_last_seen", "_n_seen", "_price_first_seen",
    "subject", "price", "price_string", "size", "deposit",
    "region_name", "area_name", "ward_name", "street_name", "longitude", "latitude",
    "account_id", "account_name", "company_ad", "furnishing_rent", "list_time",
    "orig_list_time", "number_of_images", "body", "_crawled_at",
]
EXCEL_CELL_LIMIT = 32_000


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def list_sources() -> List[Tuple[str, Path]]:
    """(crawl_date, path) for every source, oldest first."""
    sources: List[Tuple[str, Path]] = []
    if RAW_JSONL_PATH.exists():
        first = next(_iter_jsonl(RAW_JSONL_PATH), {})
        base_day = str(first.get("_crawled_at", "2026-11-10"))[:10]
        sources.append((base_day, RAW_JSONL_PATH))
    for p in sorted(SNAPSHOT_DIR.glob("????-??-??.jsonl.gz")):
        sources.append((p.name[:10], p))
    return sorted(sources, key=lambda s: s[0])


def merge_all() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    merged: Dict[int, Dict[str, Any]] = {}
    per_source = []
    for day, path in list_sources():
        n_rows, ids = 0, set()
        for ad in _iter_jsonl(path):
            try:
                ad_id = int(ad["ad_id"])
            except Exception:
                continue
            n_rows += 1
            if ad_id in ids:  # duplicate inside the same crawl
                continue
            ids.add(ad_id)
            prev = merged.get(ad_id)
            ad["_first_seen"] = prev["_first_seen"] if prev else day
            ad["_price_first_seen"] = prev["_price_first_seen"] if prev else ad.get("price")
            ad["_n_seen"] = (prev["_n_seen"] if prev else 0) + 1
            ad["_last_seen"] = day
            merged[ad_id] = ad  # newest version wins
        per_source.append({"crawl_date": day, "file": str(path.relative_to(DATA_RAW_DIR.parent.parent)),
                           "rows": n_rows, "unique_ads": len(ids)})
        logger.info(f"{day}: {n_rows} rows, {len(ids)} unique ads ({path.name}) -> running total {len(merged)}")

    records = list(merged.values())
    meta = {
        "merged_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "sources": per_source,
        "total_unique_ads": len(records),
        "seen_in_multiple_crawls": sum(1 for r in records if r["_n_seen"] > 1),
        "price_changed_between_crawls": sum(
            1 for r in records if r["_n_seen"] > 1 and r.get("price") != r.get("_price_first_seen")
        ),
    }
    return records, meta


def _flatten_for_table(records: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    df["ad_url"] = "https://www.nhatot.com/" + df["list_id"].astype(str) + ".htm"
    cols = [c for c in PRIORITY_COLS if c in df.columns] + [c for c in df.columns if c not in PRIORITY_COLS]
    df = df[cols]
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x)
        if df[col].dtype == "object":
            df[col] = (
                df[col].astype(str)
                .str.replace("\r\n", " ", regex=False).str.replace("\n", " ", regex=False).str.replace("\r", " ", regex=False)
                .replace({"nan": None, "None": None})
            )
    return df


def write_interim_parquet(records: List[Dict[str, Any]]) -> None:
    """Interim layer for src.cleaner: nested fields as JSON strings, mixed-type columns as strings."""
    df = pd.DataFrame(records)
    for col in df.columns:
        s = df[col]
        if s.apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = s.apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else (None if pd.isna(x) else str(x)))
        elif s.dtype == "object" and s.dropna().map(type).nunique() > 1:
            df[col] = s.apply(lambda x: None if pd.isna(x) else str(x))
    INTERIM_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(INTERIM_PARQUET_PATH, index=False)
    logger.info(f"Saved interim parquet for the cleaning pipeline: {INTERIM_PARQUET_PATH} ({len(df)} rows)")


def write_outputs(records: List[Dict[str, Any]], meta: Dict[str, Any]) -> pd.DataFrame:
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(MERGED_JSONL_GZ, "wt", encoding="utf-8", compresslevel=9) as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info(f"Saved {MERGED_JSONL_GZ} ({MERGED_JSONL_GZ.stat().st_size / 1e6:.1f} MB)")

    df = _flatten_for_table(records)
    df.to_csv(MERGED_CSV, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {MERGED_CSV} ({len(df)} rows x {df.shape[1]} cols, {MERGED_CSV.stat().st_size / 1e6:.1f} MB)")

    df_x = df.copy()
    for col in df_x.columns:  # Excel hard limit is 32,767 characters per cell
        if df_x[col].dtype == "object":
            df_x[col] = df_x[col].str.slice(0, EXCEL_CELL_LIMIT)
    try:
        df_x.to_excel(MERGED_XLSX, index=False, engine="openpyxl")
        logger.info(f"Saved {MERGED_XLSX} ({MERGED_XLSX.stat().st_size / 1e6:.1f} MB)")
    except Exception as e:
        logger.warning(f"Could not save Excel: {e}")

    write_interim_parquet(records)

    meta["columns"] = int(df.shape[1])
    meta["by_region"] = {k: int(v) for k, v in df["region_name"].value_counts().items()}
    with open(MERGED_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return df


if __name__ == "__main__":
    recs, info = merge_all()
    write_outputs(recs, info)
    print(json.dumps(info, ensure_ascii=False, indent=2))
