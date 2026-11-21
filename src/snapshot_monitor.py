"""Health checks & status report for the daily snapshot crawl (data/raw/snapshots/).

Used in two places:
1. src.crawler.crawl_daily_snapshot() calls validate_snapshot() right after each crawl and
   only keeps the new snapshot if it passes (a bad run never overwrites a good one).
2. CLI status report:
       python -m src.snapshot_monitor          # human-readable table + warnings
       python -m src.snapshot_monitor --json   # machine-readable
   Exit code 0 = healthy, 1 = something needs attention.
"""

import argparse
import datetime
import gzip
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.config import SNAPSHOT_DIR

STATUS_HISTORY_PATH = SNAPSHOT_DIR / "status_history.jsonl"

# Validation thresholds
MIN_TOTAL_RECORDS = 2000          # a full crawl at 300/district returns ~5,000
MIN_RATIO_VS_RECENT = 0.60        # total must be >= 60% of the median of the last 7 good snapshots
MAX_FAILED_REQUEST_RATIO = 0.10   # > 10% failed HTTP requests -> reject
DISTRICT_DROP_RATIO = 0.30        # a district that usually has >= 100 ads but now < 30% of usual -> reject


def _load_metadata(meta_path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_snapshot_metadata() -> List[Tuple[str, Dict[str, Any]]]:
    """(date, metadata) of every kept snapshot, oldest first."""
    out = []
    for p in sorted(SNAPSHOT_DIR.glob("????-??-??_metadata.json")):
        day = p.name[:10]
        meta = _load_metadata(p)
        if meta is not None and (SNAPSHOT_DIR / f"{day}.jsonl.gz").exists():
            out.append((day, meta))
    return out


def validate_snapshot(meta: Dict[str, Any], previous: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str]]:
    """Return (ok, errors, warnings) for a freshly crawled snapshot."""
    errors: List[str] = []
    warnings: List[str] = []
    total = int(meta.get("total_raw_records_this_run", 0))
    n_req = int(meta.get("total_requests", 0)) or 1
    n_fail = int(meta.get("failed_requests", 0))

    if total < MIN_TOTAL_RECORDS:
        errors.append(f"Chỉ thu được {total} tin (< {MIN_TOTAL_RECORDS})")

    recent = [int(m.get("total_raw_records_this_run", 0)) for m in previous[-7:]]
    if recent:
        med = statistics.median(recent)
        if total < MIN_RATIO_VS_RECENT * med:
            errors.append(f"Tổng {total} tin < {int(MIN_RATIO_VS_RECENT * 100)}% trung vị 7 đợt gần nhất ({int(med)})")

    if n_fail / n_req > MAX_FAILED_REQUEST_RATIO:
        errors.append(f"{n_fail}/{n_req} request lỗi (> {int(MAX_FAILED_REQUEST_RATIO * 100)}%)")
    elif n_fail:
        warnings.append(f"{n_fail}/{n_req} request lỗi (dưới ngưỡng, vẫn giữ)")

    if previous:
        usual: Dict[str, List[int]] = {}
        for m in previous[-7:]:
            for k, v in m.get("records_per_district", {}).items():
                usual.setdefault(k, []).append(int(v))
        now = meta.get("records_per_district", {})
        for district, hist in usual.items():
            typical = statistics.median(hist)
            got = int(now.get(district, 0))
            if typical >= 100 and got < DISTRICT_DROP_RATIO * typical:
                errors.append(f"{district}: {got} tin, thường ~{int(typical)}")
    return (not errors), errors, warnings


def record_status(entry: Dict[str, Any]) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"logged_at": datetime.datetime.now().isoformat(timespec="seconds"), **entry}
    with open(STATUS_HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_status_history() -> List[Dict[str, Any]]:
    if not STATUS_HISTORY_PATH.exists():
        return []
    rows = []
    with open(STATUS_HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def _ad_ids(day: str) -> Set[int]:
    ids: Set[int] = set()
    with gzip.open(SNAPSHOT_DIR / f"{day}.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            try:
                ids.add(int(json.loads(line)["ad_id"]))
            except Exception:
                pass
    return ids


def build_report() -> Dict[str, Any]:
    snaps = list_snapshot_metadata()
    today = datetime.date.today()
    rows = []
    seen_all: Set[int] = set()
    prev_ids: Optional[Set[int]] = None
    for day, meta in snaps:
        ids = _ad_ids(day)
        rows.append({
            "date": day,
            "records": int(meta.get("total_raw_records_this_run", 0)),
            "unique_ads": len(ids),
            "new_vs_prev_day": len(ids - prev_ids) if prev_ids is not None else None,
            "gone_vs_prev_day": len(prev_ids - ids) if prev_ids is not None else None,
            "new_ever": len(ids - seen_all),
            "failed_requests": int(meta.get("failed_requests", 0)),
            "duration_min": meta.get("duration_minutes"),
            "size_mb": round((SNAPSHOT_DIR / f"{day}.jsonl.gz").stat().st_size / 1e6, 1),
        })
        seen_all |= ids
        prev_ids = ids

    issues: List[str] = []
    missing: List[str] = []
    if snaps:
        first = datetime.date.fromisoformat(snaps[0][0])
        have = {d for d, _ in snaps}
        d = first
        while d <= today:
            if d.isoformat() not in have:
                missing.append(d.isoformat())
            d += datetime.timedelta(days=1)
        # Today's run is scheduled for 21:00; only flag today if it is already late evening
        if missing and missing[-1] == today.isoformat() and datetime.datetime.now().hour < 23:
            missing = missing[:-1]
        if missing:
            issues.append(f"Thiếu snapshot các ngày: {', '.join(missing)}")
        last = datetime.date.fromisoformat(snaps[-1][0])
        if (today - last).days >= 2:
            issues.append(f"Đã {(today - last).days} ngày không có snapshot mới (lần cuối {last})")
    else:
        issues.append("Chưa có snapshot nào")

    history = read_status_history()
    last_status = history[-1] if history else None
    if last_status and not last_status.get("ok", True):
        issues.append(f"Lần chạy gần nhất ({last_status.get('date')}) THẤT BẠI: {last_status.get('errors')}")

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "n_snapshots": len(snaps),
        "unique_ads_all_snapshots": len(seen_all),
        "snapshots": rows,
        "missing_days": missing,
        "last_run": last_status,
        "issues": issues,
        "healthy": not issues,
    }


def print_report(rep: Dict[str, Any]) -> None:
    print(f"=== TÌNH TRẠNG CRAWL HẰNG NGÀY ({rep['generated_at']}) ===")
    print(f"Số snapshot: {rep['n_snapshots']} | Tổng tin không trùng qua các ngày: {rep['unique_ads_all_snapshots']:,}")
    print(f"{'Ngày':<12}{'Tin':>7}{'Mới/hôm qua':>13}{'Mất/hôm qua':>13}{'Mới hẳn':>9}{'Req lỗi':>9}{'Phút':>7}{'MB':>6}")
    for r in rep["snapshots"]:
        nv = "-" if r["new_vs_prev_day"] is None else r["new_vs_prev_day"]
        gv = "-" if r["gone_vs_prev_day"] is None else r["gone_vs_prev_day"]
        print(f"{r['date']:<12}{r['records']:>7}{nv:>13}{gv:>13}{r['new_ever']:>9}{r['failed_requests']:>9}"
              f"{r['duration_min'] or 0:>7}{r['size_mb']:>6}")
    if rep["last_run"]:
        lr = rep["last_run"]
        print(f"Lần chạy gần nhất: {lr.get('logged_at')} -> {'OK' if lr.get('ok') else 'THẤT BẠI'}"
              + (f" | cảnh báo: {lr.get('warnings')}" if lr.get("warnings") else ""))
    if rep["issues"]:
        print("\n⚠️  CẦN XỬ LÝ:")
        for i in rep["issues"]:
            print(f"  - {i}")
    else:
        print("\n✅ Ổn định — không có vấn đề.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Daily snapshot crawl status")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    args = ap.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    sys.exit(0 if report["healthy"] else 1)
