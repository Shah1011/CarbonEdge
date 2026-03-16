# ...existing code...
import os
import csv
import time
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
import requests

def get_last_timestamps_from_csv(path: str) -> Dict[Tuple[str, str], str]:
    """
    Returns a dict mapping (provider, region) -> latest timestamp (ISO string) found in the CSV.
    """
    if not os.path.exists(path):
        return {}
    last_ts: Dict[Tuple[str, str], str] = {}
    with open(path, "r", encoding=CSV_ENCODING) as f:
        reader = csv.DictReader(f)
        for row in reader:
            provider = row.get("provider")
            region = row.get("region")
            ts = row.get("timestamp")
            if provider and region and ts:
                key = (provider, region)
                # Keep the max timestamp (ISO 8601 sorts lexicographically)
                if key not in last_ts or ts > last_ts[key]:
                    last_ts[key] = ts
    return last_ts
# Add YAML support
try:
    import yaml
except ImportError:
    yaml = None

# ========= USER CONFIG =========

# 1) Auth
API_TOKEN = "iGicrQqXZWQazxMFP5Qn"
AUTH_HEADER = {"auth-token": API_TOKEN}

# 2) Endpoint
BASE_URL = "https://api.electricitymaps.com/v3/carbon-intensity/past-range"

USE_PROVIDER_REGION_YAML = True  # Set to True to use YAML, False to use CSV
PROVIDER_REGION_YAML = "providers_regions.yaml"  # format: provider: [region1, region2, ...]


def load_regions_from_yaml(path: str) -> Dict[str, Dict[str, str]]:
    import re
    if yaml is None:
        raise ImportError("PyYAML is required to load regions from a YAML file. Install with 'pip install pyyaml'.")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Region YAML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Support nested structure: {cloud_regions: {provider: {region: name, ...}, ...}}
    if "cloud_regions" in data:
        data = data["cloud_regions"]
    
    by_provider: Dict[str, Dict[str, str]] = {}
    region_code_pattern = re.compile(r"^[a-z]{2,}-[a-z]+-\d+$", re.IGNORECASE)  # e.g., us-east-1
    for provider, region_map in data.items():
        if not isinstance(region_map, dict):
            continue
        region_dict = {}
        for r in region_map:
            if not r or not isinstance(r, str):
                continue
            val = region_map[r]
            # Use value if it's a short uppercase code (like SG) or matches region pattern, otherwise use key
            if val and isinstance(val, str):
                val_stripped = val.strip()
                # Check if value is a 2-3 letter uppercase code OR matches region code pattern
                if (len(val_stripped) <= 3 and val_stripped.isupper()) or region_code_pattern.match(val_stripped):
                    region_dict[r.strip()] = val_stripped
                    print(f"DEBUG: Mapping {r.strip()} -> {val_stripped}")
                else:
                    region_dict[r.strip()] = r.strip()
            else:
                region_dict[r.strip()] = r.strip()
        by_provider[provider.strip().lower()] = region_dict
    return by_provider

# 4) Time window (from 2022-01-01)
END_UTC = datetime.now(timezone.utc)
START_UTC = datetime(2022, 1, 1, tzinfo=timezone.utc)

# 5) Windowing constraints
WINDOW_DAYS = 10  # API range limit
REQUESTS_PER_MINUTE = 30  # adjust to your plan
REQUEST_SPACING_SEC = max(0.0, 60.0 / REQUESTS_PER_MINUTE)

# 6) Retry/timeout
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
TIMEOUT_SEC = 30


# 7) Output CSVs (per provider/region)
CSV_ENCODING = "utf-8"
CSV_DIALECT = "excel"
FIELDNAMES = ["timestamp", "provider", "region", "carbon_intensity", "unit"]

def get_output_csv_path(provider: str, region: str) -> str:
    folder = provider.lower()
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{region}.csv")

def get_last_timestamp_for_region_csv(path: str) -> Optional[str]:
    """
    Returns the latest timestamp (ISO string) found in the region CSV, or None if not present.
    """
    if not os.path.exists(path):
        return None
    last_ts: Optional[str] = None
    with open(path, "r", encoding=CSV_ENCODING) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = row.get("timestamp")
            if ts and (last_ts is None or ts > last_ts):
                last_ts = ts
    return last_ts

# 8) Parsing fallback keys (robust to minor schema differences)
# Expected shapes include:
# - Top-level list of points
# - Or {"history": [ ... ]}, {"data": [ ... ]}, {"points": [ ... ]}
CANDIDATE_LIST_KEYS = [None, "history", "data", "points"]
TIME_KEYS = ["datetime", "timestamp", "time"]
VALUE_KEYS = ["carbonIntensity", "value", "intensity"]
UNIT_KEYS = ["unit"]
FALLBACK_UNIT = "gCO2eq/kWh"


# ========= HELPERS =========

def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ten_day_spans(start_dt: datetime, end_dt: datetime, window_days: int = WINDOW_DAYS) -> List[Tuple[datetime, datetime]]:
    if start_dt >= end_dt:
        return []
    spans = []
    cur = start_dt
    window = timedelta(days=window_days)
    while cur < end_dt:
        nxt = cur + window
        if nxt > end_dt:
            nxt = end_dt
        # Make end slightly less than next start to mitigate inclusive boundary duplicates
        span_end = nxt - timedelta(seconds=1) if nxt != end_dt else end_dt
        spans.append((cur, span_end))
        # Next window starts one second after previous end
        cur = span_end + timedelta(seconds=1)
    return spans


def ensure_csv_with_header(path: str, fieldnames: List[str]) -> None:
    need_header = (not os.path.exists(path)) or (os.path.getsize(path) == 0)
    if need_header:
        with open(path, "w", newline="", encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, dialect=CSV_DIALECT)
            writer.writeheader()


def append_csv_rows(path: str, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "a", newline="", encoding=CSV_ENCODING) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, dialect=CSV_DIALECT)
        writer.writerows(rows)


def do_request(params: Dict[str, Any]) -> requests.Response:
    backoff = INITIAL_BACKOFF
    last_exc: Optional[Exception] = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=AUTH_HEADER, timeout=TIMEOUT_SEC)
            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    try:
                        sleep_s = float(retry_after)
                    except ValueError:
                        sleep_s = backoff
                else:
                    sleep_s = backoff
                time.sleep(sleep_s)
                backoff = min(backoff * 2, 60.0)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)

    if last_exc:
        raise last_exc
    raise RuntimeError("Request failed after retries with no exception detail.")


def choose_first_key(item: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for k in keys:
        if k in item:
            return k
    return None


def extract_list(payload: Any) -> List[Dict[str, Any]]:
    # Try known container keys; if None is present, treat payload as list
    for key in CANDIDATE_LIST_KEYS:
        if key is None and isinstance(payload, list):
            return payload
        if key is not None and isinstance(payload, dict) and key in payload and isinstance(payload[key], list):
            return payload[key]
    # If dict has a single list value, use it
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return v
    raise ValueError("Unable to locate list of points in response payload.")


def parse_points(payload: Any, provider: str, region: str, last_seen_ts: Optional[str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Returns (rows, new_last_seen_ts).
    Deduplicates the first record if it matches last_seen_ts (boundary overlap).
    """
    data_list = extract_list(payload)
    rows: List[Dict[str, Any]] = []
    max_ts: Optional[str] = last_seen_ts

    for item in data_list:
        t_key = choose_first_key(item, TIME_KEYS)
        v_key = choose_first_key(item, VALUE_KEYS)
        u_key = choose_first_key(item, UNIT_KEYS)

        if t_key is None or v_key is None:
            # Skip malformed points
            continue

        ts = item[t_key]
        val = item[v_key]
        unit = item.get(u_key, FALLBACK_UNIT) if u_key else FALLBACK_UNIT

        # boundary de-duplication
        if last_seen_ts is not None and ts == last_seen_ts:
            continue

        rows.append({
            "timestamp": ts,
            "provider": provider,
            "region": region,
            "carbon_intensity": val,
            "unit": unit,
        })

        # Track max timestamp seen for next chunk
        # ISO 8601 strings are lexicographically comparable for UTC Z format
        if isinstance(ts, str):
            if max_ts is None or ts > max_ts:
                max_ts = ts

    return rows, max_ts


def load_regions_from_csv(path: str) -> Dict[str, List[str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Region CSV not found: {path}")
    by_provider: Dict[str, List[str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        # Accept with or without header; expect columns: provider,region
        for row in reader:
            if not row or len(row) < 2:
                continue
            provider = row[0].strip().lower()
            region = row[1].strip()
            if not provider or not region:
                continue
            by_provider.setdefault(provider, []).append(region)
    return by_provider


def main() -> None:
    if not API_TOKEN or API_TOKEN == "YOUR_API_TOKEN_PLACEHOLDER":
        print("ERROR: Set ELECTRICITYMAP_TOKEN env var or edit API_TOKEN.", file=sys.stderr)
        sys.exit(1)


    # Regions
    providers_regions: Dict[str, List[str]] = {}
    try:
        providers_regions = load_regions_from_yaml(PROVIDER_REGION_YAML)
    except Exception as e:
        print(f"ERROR: Failed to load regions from YAML: {e}", file=sys.stderr)
        sys.exit(1)

    if not providers_regions:
        print("ERROR: No regions provided. Populate providers_regions.yaml, providers_regions.csv, or REGIONS_BY_PROVIDER.", file=sys.stderr)
        sys.exit(1)


    spans = ten_day_spans(START_UTC, END_UTC, WINDOW_DAYS)
    providers = sorted(providers_regions.keys())
    print(f"Providers: {providers}")
    for provider in providers:
        regions = sorted(providers_regions.get(provider, []))
        print(f"Provider '{provider}' regions: {len(regions)}")

    print(f"Time spans: {len(spans)} windows of up to {WINDOW_DAYS} days each.")
    print("Starting fetch...")

    done = 0
    for provider, regions in providers_regions.items():
        for region in regions:
            region_csv = get_output_csv_path(provider, region)
            ensure_csv_with_header(region_csv, FIELDNAMES)
            region_last_ts = get_last_timestamp_for_region_csv(region_csv)

            for s, e in spans:
                # If resuming, skip this window if its end is before the last timestamp
                if region_last_ts is not None and iso_z(e) <= region_last_ts:
                    continue

                params = {
                    "dataCenterProvider": provider,
                    "dataCenterRegion": region,
                    "start": iso_z(s),
                    "end": iso_z(e),
                }

                try:
                    resp = do_request(params)
                    payload = resp.json()
                except Exception as ex:
                    print(f"[WARN] Request failed provider={provider} region={region} {s.date()}..{e.date()}: {ex}", file=sys.stderr)
                    time.sleep(REQUEST_SPACING_SEC)
                    continue

                try:
                    rows, new_last = parse_points(payload, provider, region, region_last_ts)
                except Exception as ex:
                    snippet = json.dumps(payload, ensure_ascii=False)[:600]
                    print(f"[ERROR] Parsing failed provider={provider} region={region} {s.date()}..{e.date()}: {ex}\nPayload head: {snippet}", file=sys.stderr)
                    time.sleep(REQUEST_SPACING_SEC)
                    continue

                append_csv_rows(region_csv, FIELDNAMES, rows)
                region_last_ts = new_last
                done += 1

                print(f"Done {done}: {provider}/{region} {s.date()}..{e.date()} -> {len(rows)} rows")
                time.sleep(REQUEST_SPACING_SEC)

    print(f"All done. Output: aws/ and azure/ folders with region CSVs.")


if __name__ == "__main__":
    main()