"""Local Socrata discovery and resumable monthly extraction (Python 3.12+)."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import gzip
from http.client import IncompleteRead
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time
import tracemalloc
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "research/config/nyc_ems_2026.json"


class PipelineError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2).encode("utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def save_json(path, value):
    atomic_write(path, encode(value))


def repository_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise PipelineError("Configured path must remain inside the repository")
    return path


def load_config(path):
    config = read_json(path)
    source = config["source"]
    dictionary = repository_path(source["dictionary_path"])
    if digest(dictionary.read_bytes()) != source["dictionary_sha256"]:
        raise PipelineError("Original dictionary checksum differs from configuration")
    with repository_path(source["field_contract_path"]).open(encoding="utf-8", newline="") as handle:
        fields = list(csv.DictReader(handle))
    columns = config["extraction"]["columns"]
    if columns != [field["field"] for field in fields] or len(set(columns)) != len(columns):
        raise PipelineError("Selected fields differ from the field contract or contain duplicates")
    if config["extraction"]["quality_filters_at_source"]:
        raise PipelineError("Pilot must preserve all source rows in its date window")
    if config["extraction"]["order_by"] != ["incident_datetime", "incident_id"]:
        raise PipelineError("Pilot requires stable datetime/ID ordering")
    if config["extraction"]["page_size"] < 1:
        raise PipelineError("Page size must be positive")
    window = config["window"]
    start, end = pilot_window(config)
    if not window["start_inclusive"] <= start < end <= window["end_exclusive"]:
        raise PipelineError("Pilot is outside the frozen study window")
    datetime.fromisoformat(start)
    datetime.fromisoformat(end)
    return config


def lineage(config):
    return {
        "config_sha256": digest(encode(config)),
        "dictionary_sha256": digest(repository_path(config["source"]["dictionary_path"]).read_bytes()),
        "field_contract_sha256": digest(repository_path(config["source"]["field_contract_path"]).read_bytes()),
        "mappings_sha256": digest(repository_path(config["source"]["mappings_path"]).read_bytes()),
        "extractor_sha256": digest(Path(__file__).read_bytes()),
        "python_version": platform.python_version(),
    }


def pilot_window(config):
    return config["window"]["pilot_start_inclusive"], config["window"]["pilot_end_exclusive"]


def selected_window(config, mode):
    if mode == "pilot":
        return pilot_window(config)
    if mode != "full":
        raise PipelineError("Unknown extraction mode")
    return config["window"]["start_inclusive"], config["window"]["end_exclusive"]


def partitions(config, evidence, mode):
    start, end = selected_window(config, mode)
    daily = {row["day"][:10]: int(row["incidents"]) for row in evidence["days"]["rows"]}
    result = []
    cursor = datetime.fromisoformat(start)
    finish = datetime.fromisoformat(end)
    while cursor < finish:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1, hour=0, minute=0, second=0)
        boundary = min(next_month, finish)
        count = sum(count for day, count in daily.items() if cursor.date().isoformat() <= day < boundary.date().isoformat())
        result.append({"month": cursor.strftime("%Y-%m"), "start_inclusive": cursor.isoformat(),
                       "end_exclusive": boundary.isoformat(), "expected_rows": count})
        cursor = boundary
    return result


def page_position(manifest, total):
    parts = manifest.get("partitions", [{**manifest["window"], "month": manifest["window"]["start_inclusive"][:7],
                                          "expected_rows": manifest["expected_rows"]}])
    for part in parts:
        if total < part["expected_rows"]:
            return part, total
        total -= part["expected_rows"]
    raise PipelineError("Page extends beyond the declared partitions")


def date_filter(start, end):
    # Only validated ISO dates are interpolated into SoQL literals.
    for value in (start, end):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
            raise PipelineError("Expected an ISO local timestamp with second precision")
        datetime.fromisoformat(value)
    return f"incident_datetime >= '{start}' AND incident_datetime < '{end}'"


def retry_delay(header, fallback):
    if not header:
        return fallback
    try:
        return max(0, float(header))
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return fallback


class SocrataClient:
    def __init__(self, config):
        self.config = config
        self.requests = 0
        self.response_bytes = 0

    def request(self, endpoint, params=None):
        url = endpoint + ("?" + urlencode(params) if params else "")
        headers = {"Accept": "application/json", "User-Agent": "EMS-Research-Extractor/2.0"}
        token = os.environ.get(self.config["source"]["app_token_env"])
        if token:
            headers["X-App-Token"] = token
        options = self.config["extraction"]
        for attempt in range(options["max_attempts"]):
            delay = min(options["backoff_max_seconds"], options["backoff_initial_seconds"] * 2**attempt)
            self.requests += 1
            try:
                with urlopen(Request(url, headers=headers), timeout=options["timeout_seconds"]) as response:
                    raw = response.read()
                self.response_bytes += len(raw)
                value = json.loads(raw)
                if isinstance(value, dict) and value.get("error"):
                    raise PipelineError("Socrata returned an error object; check query/schema")
                return value, raw, url
            except HTTPError as error:
                code = error.code
                if options["respect_retry_after"]:
                    delay = retry_delay(error.headers.get("Retry-After"), delay)
                error.close()
                if code not in options["retry_http_statuses"]:
                    raise PipelineError(f"Socrata HTTP {code}; request not retryable") from None
            except (URLError, TimeoutError, ConnectionError, IncompleteRead):
                pass
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise PipelineError("Response is not valid JSON") from None
            if attempt + 1 == options["max_attempts"]:
                raise PipelineError("Socrata unavailable after bounded retries; local pages preserved")
            print(f"Transient request failure; retry {attempt + 2} in {delay:.1f}s", flush=True)
            time.sleep(delay)
        raise PipelineError("No request attempts configured")

    def query(self, params):
        value, raw, url = self.request(self.config["source"]["endpoint"], params)
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            raise PipelineError("Expected a Socrata row array")
        return value, raw, url

    def metadata(self):
        return self.request(self.config["source"]["metadata_endpoint"])[0]


def schema_guard(metadata, config):
    columns = {column["fieldName"]: column["dataTypeName"] for column in metadata["columns"]}
    with repository_path(config["source"]["field_contract_path"]).open(encoding="utf-8", newline="") as handle:
        for field in csv.DictReader(handle):
            expected = {"string": "text", "local_datetime": "calendar_date", "number": "number"}[field["normalized_type"]]
            if columns.get(field["field"]) != expected:
                raise PipelineError(f"Source schema mismatch: {field['field']} must be {expected}")
    if metadata.get("rowsUpdatedAt") is None:
        raise PipelineError("Missing source update marker")
    return digest(encode({"rowsUpdatedAt": metadata["rowsUpdatedAt"], "columns": columns}))


def aggregate(client, params):
    params = {**params, "$limit": 1000}
    rows, _, url = client.query(params)
    if len(rows) >= 1000:
        raise PipelineError("Discovery aggregation may be truncated")
    return {"query": url, "rows": rows}


def discover(client, config, mode="pilot"):
    before = client.metadata()
    marker = schema_guard(before, config)
    start, end = pilot_window(config)
    study = config["window"]
    evidence = {
        "checked_at": utc_now(),
        "metadata": before,
        "source_marker": marker,
        "latest": aggregate(client, {"$select": "min(incident_datetime) as earliest,max(incident_datetime) as latest"}),
        "months": aggregate(client, {
            "$select": "date_trunc_ym(incident_datetime) as month,count(*) as incidents",
            "$where": date_filter(study["start_inclusive"], study["end_exclusive"]),
            "$group": "date_trunc_ym(incident_datetime)", "$order": "month",
        }),
        "days": aggregate(client, {
            "$select": "date_trunc_ymd(incident_datetime) as day,count(*) as incidents",
            "$where": date_filter(study["start_inclusive"], study["end_exclusive"]),
            "$group": "date_trunc_ymd(incident_datetime)", "$order": "day",
        }),
        "pilot": aggregate(client, {
            "$select": "count(*) as incidents,count(distinct incident_id) as unique_ids",
            "$where": date_filter(start, end),
        }),
    }
    if mode == "full":
        evidence["full"] = aggregate(client, {
            "$select": "count(*) as incidents,count(distinct incident_id) as unique_ids",
            "$where": date_filter(*selected_window(config, mode)),
        })
    after = client.metadata()
    if marker != schema_guard(after, config):
        raise PipelineError("Source changed during discovery; create a new attempt")
    evidence["metadata_after"] = after
    pilot = evidence["pilot"]["rows"]
    if len(pilot) != 1 or int(pilot[0]["incidents"]) < 1:
        raise PipelineError("Pilot window has no published incidents")
    if int(pilot[0]["incidents"]) != int(pilot[0]["unique_ids"]):
        raise PipelineError("Pilot IDs are not unique; stable pagination requires review")
    day_counts = {row["day"][:10]: int(row["incidents"]) for row in evidence["days"]["rows"]}
    missing = []
    date = datetime.fromisoformat(study["start_inclusive"])
    while date < datetime.fromisoformat(study["end_exclusive"]):
        if date.date().isoformat() not in day_counts:
            missing.append(date.date().isoformat())
        date += timedelta(days=1)
    evidence["study_days_without_records"] = missing
    expected_pilot_days = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
    covered_pilot_days = [day for day in day_counts if start[:10] <= day < end[:10]]
    if len(covered_pilot_days) != expected_pilot_days:
        raise PipelineError("Pilot has dates without published records; review coverage")
    if sum(day_counts[day] for day in covered_pilot_days) != int(pilot[0]["incidents"]):
        raise PipelineError("Pilot aggregate and daily counts disagree")
    if sum(day_counts.values()) != sum(int(row["incidents"]) for row in evidence["months"]["rows"]):
        raise PipelineError("Monthly and daily discovery counts disagree")
    if mode == "full":
        full = evidence["full"]["rows"]
        if len(full) != 1 or int(full[0]["incidents"]) != sum(day_counts.values()):
            raise PipelineError("Full-window and daily counts disagree")
        if int(full[0]["incidents"]) != int(full[0]["unique_ids"]):
            raise PipelineError("Full-window IDs are not unique; review before extraction")
        if missing:
            raise PipelineError("Full window has dates without records; review coverage")
    return evidence


def evidence_signature(evidence):
    return digest(encode({key: evidence[key] for key in ("source_marker", "months", "days", "pilot", "full") if key in evidence}))


def create_snapshot(config):
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + digest(encode(config))[:12]
    folder = repository_path(config["paths"]["data_root"]) / snapshot_id
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def get_snapshot(config, snapshot_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", snapshot_id):
        raise PipelineError("Invalid snapshot ID")
    folder = repository_path(config["paths"]["data_root"]) / snapshot_id
    if not folder.is_dir():
        raise PipelineError("Snapshot does not exist")
    return folder


def save_discovery(folder, config, evidence, mode="pilot"):
    save_json(folder / "config.json", config)
    save_json(folder / "discovery.json", evidence)
    manifest = {
        "manifest_version": "2.0.0", "study_id": config["study_id"],
        "snapshot_id": folder.name, "mode": mode, "status": "discovered",
        "created_at": utc_now(), "lineage": lineage(config),
        "window": dict(zip(("start_inclusive", "end_exclusive"), selected_window(config, mode))),
        "partitions": partitions(config, evidence, mode),
        "source_timezone": config["window"]["source_timezone"],
        "discovery_sha256": digest((folder / "discovery.json").read_bytes()),
        "expected_rows": int(evidence["full" if mode == "full" else "pilot"]["rows"][0]["incidents"]),
        "pages": [], "sessions": [],
    }
    artifacts = {
        "dictionary.csv": repository_path(config["source"]["dictionary_path"]),
        "fields.csv": repository_path(config["source"]["field_contract_path"]),
        "mappings.json": repository_path(config["source"]["mappings_path"]),
        "extractor.py": Path(__file__),
    }
    manifest["provenance_files"] = {}
    for name, path in artifacts.items():
        raw = path.read_bytes()
        atomic_write(folder / "provenance" / name, raw)
        manifest["provenance_files"][name] = digest(raw)
    save_json(folder / "manifest.json", manifest)
    return manifest


def inspect_pages(folder, manifest, config):
    seen = set()
    previous = None
    ids_hash = hashlib.sha256()
    missing = Counter()
    categories = {field: Counter() for field in config["extraction"]["columns"] if field.endswith("indicator") or field.endswith("indc") or field == "borough"}
    daily = Counter()
    total = compressed = raw_bytes = 0
    for page in manifest["pages"]:
        part, offset = page_position(manifest, total)
        start, end = (datetime.fromisoformat(part[key]) for key in ("start_inclusive", "end_exclusive"))
        expected_path = f"raw/{part['month']}/page-{offset:09d}.json.gz"
        if page["offset"] != offset or page["path"] != expected_path:
            raise PipelineError("Manifest page sequence/path is invalid")
        binary = (folder / expected_path).read_bytes()
        if digest(binary) != page["sha256"]:
            raise PipelineError(f"Page checksum mismatch at offset {total}")
        raw = gzip.decompress(binary)
        if digest(raw) != page["raw_sha256"]:
            raise PipelineError("Uncompressed page checksum mismatch")
        rows = json.loads(raw)
        expected_rows = min(config["extraction"]["page_size"], part["expected_rows"] - offset)
        if len(rows) != page["rows"] or len(rows) != expected_rows:
            raise PipelineError("Page row count invalid")
        if len(binary) != page["compressed_bytes"] or len(raw) != page["raw_bytes"]:
            raise PipelineError("Page byte counts invalid")
        for row in rows:
            incident_id = row.get("incident_id")
            timestamp = row.get("incident_datetime")
            if not isinstance(incident_id, str) or not incident_id or not isinstance(timestamp, str):
                raise PipelineError("Missing ID/date in raw page; inspect source before resuming")
            moment = datetime.fromisoformat(timestamp)
            key = (moment, incident_id)
            if not start <= moment < end or (previous is not None and key <= previous):
                raise PipelineError("Rows outside pilot/partition window or not strictly ordered")
            if incident_id in seen:
                raise PipelineError("Duplicate ID across downloaded rows")
            seen.add(incident_id)
            previous = key
            ids_hash.update(encode([timestamp, incident_id]))
            daily[timestamp[:10]] += 1
            for field in config["extraction"]["columns"]:
                if row.get(field) is None:
                    missing[field] += 1
            for field, counts in categories.items():
                counts[str(row[field]) if row.get(field) is not None else "<missing>"] += 1
        total += len(rows)
        compressed += len(binary)
        raw_bytes += len(raw)
    if total > manifest["expected_rows"]:
        raise PipelineError("More local rows than expected")
    return {
        "rows": total, "unique_ids": len(seen), "ordered_ids_sha256": ids_hash.hexdigest(),
        "compressed_bytes": compressed, "raw_bytes": raw_bytes, "daily_counts": dict(sorted(daily.items())),
        "missing_values": {field: missing[field] for field in config["extraction"]["columns"]},
        "categories": {field: dict(sorted(counts.items())) for field, counts in categories.items()},
    }


def load_snapshot(folder, config, strict=True):
    manifest = read_json(folder / "manifest.json")
    if read_json(folder / "config.json") != config or digest(encode(config)) != manifest["lineage"]["config_sha256"]:
        raise PipelineError("Archived configuration changed or differs from its manifest")
    if strict and manifest["lineage"] != lineage(config):
        raise PipelineError("Config, dictionaries, mappings, Python or extractor changed; use a new snapshot")
    if digest((folder / "discovery.json").read_bytes()) != manifest["discovery_sha256"]:
        raise PipelineError("Discovery evidence checksum mismatch")
    if manifest["status"] == "invalidated":
        raise PipelineError("Source changed for this snapshot; create a new one")
    evidence = read_json(folder / "discovery.json")
    if manifest["manifest_version"] == "2.0.0":
        expected_files = {"dictionary.csv": "dictionary_sha256", "fields.csv": "field_contract_sha256",
                          "mappings.json": "mappings_sha256", "extractor.py": "extractor_sha256"}
        if set(manifest["provenance_files"]) != set(expected_files):
            raise PipelineError("Provenance file inventory differs")
        for name, key in expected_files.items():
            actual = digest((folder / "provenance" / name).read_bytes())
            if actual != manifest["provenance_files"][name] or actual != manifest["lineage"][key]:
                raise PipelineError("Archived provenance checksum mismatch")
        if manifest["partitions"] != partitions(config, evidence, manifest["mode"]):
            raise PipelineError("Partition plan differs from source evidence")
    elif manifest["manifest_version"] != "1.0.0":
        raise PipelineError("Unsupported manifest version")
    selected = "full" if manifest["mode"] == "full" else "pilot"
    if manifest["expected_rows"] != int(evidence[selected]["rows"][0]["incidents"]):
        raise PipelineError("Manifest count differs from discovery")
    if manifest["window"] != dict(zip(("start_inclusive", "end_exclusive"), selected_window(config, manifest["mode"]))):
        raise PipelineError("Manifest window differs from configuration")
    return manifest, evidence


DATE_FIELDS = [
    "incident_datetime",
    "first_assignment_datetime",
    "first_activation_datetime",
    "first_on_scene_datetime",
    "first_to_hosp_datetime",
    "first_hosp_arrival_datetime",
    "incident_close_datetime",
]

NUMERIC_FIELDS = [
    "initial_severity_level_code",
    "final_severity_level_code",
    "dispatch_response_seconds_qy",
    "incident_response_seconds_qy",
    "incident_travel_tm_seconds_qy",
]

FLAG_FIELDS = [
    "valid_dispatch_rspns_time_indc",
    "valid_incident_rspns_time_indc",
    "held_indicator",
    "reopen_indicator",
    "special_event_indicator",
    "standby_indicator",
    "transfer_indicator",
]


def iter_raw_rows(folder, manifest):
    for page in manifest["pages"]:
        rows = json.loads(gzip.decompress((folder / page["path"]).read_bytes()))
        for row in rows:
            yield row


def require_pandas():
    try:
        import pandas as pd
    except ImportError as error:
        raise PipelineError("Phase 3 requires pandas. Install backend/research dependencies first.") from error
    return pd


def normalize_text(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return re.sub(r"\s+", " ", text).upper()


def normalize_flag(value):
    text = normalize_text(value)
    if text == "Y":
        return True
    if text == "N":
        return False
    return None


def json_safe(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        item = value.item()
        if isinstance(item, float) and math.isnan(item):
            return None
        return item
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def dataframe_from_snapshot(folder, manifest, config):
    pd = require_pandas()
    rows = list(iter_raw_rows(folder, manifest))
    frame = pd.DataFrame.from_records(rows, columns=config["extraction"]["columns"])
    frame.insert(0, "row_number", range(1, len(frame) + 1))
    return frame


def add_cleaning_columns(frame):
    pd = require_pandas()
    clean = frame.copy()
    for field in clean.columns:
        if field not in DATE_FIELDS and field not in NUMERIC_FIELDS and field != "row_number":
            clean[field] = clean[field].map(lambda value: None if value is None or str(value).strip() == "" else str(value).strip())
    clean["incident_id_norm"] = clean["incident_id"].map(normalize_text)
    for field in ("borough", "incident_dispatch_area", "zipcode", "initial_call_type", "final_call_type", "incident_disposition_code"):
        if field in clean:
            clean[f"{field}_norm"] = clean[field].map(normalize_text)
    for field in FLAG_FIELDS:
        clean[f"{field}_bool"] = clean[field].map(normalize_flag)
    for field in NUMERIC_FIELDS:
        clean[f"{field}_num"] = pd.to_numeric(clean[field], errors="coerce")
    for field in DATE_FIELDS:
        clean[f"{field}_parsed"] = pd.to_datetime(clean[field], errors="coerce")
    clean["incident_date"] = clean["incident_datetime_parsed"].dt.date.astype("string")
    clean["incident_hour"] = clean["incident_datetime_parsed"].dt.floor("h")
    clean["borough_cohort"] = clean["borough_norm"].fillna("UNKNOWN")
    clean["has_valid_id"] = clean["incident_id_norm"].notna()
    clean["has_valid_incident_datetime"] = clean["incident_datetime_parsed"].notna()
    clean["has_usable_geography"] = clean["borough_cohort"].notna()
    clean["duplicate_incident_id"] = clean.duplicated("incident_id_norm", keep=False) & clean["incident_id_norm"].notna()
    clean["exact_duplicate"] = frame.duplicated(keep=False)
    clean["dispatch_seconds_nonnegative"] = clean["dispatch_response_seconds_qy_num"].isna() | (clean["dispatch_response_seconds_qy_num"] >= 0)
    clean["incident_seconds_nonnegative"] = clean["incident_response_seconds_qy_num"].isna() | (clean["incident_response_seconds_qy_num"] >= 0)
    clean["travel_seconds_nonnegative"] = clean["incident_travel_tm_seconds_qy_num"].isna() | (clean["incident_travel_tm_seconds_qy_num"] >= 0)
    clean["assignment_after_call"] = clean["first_assignment_datetime_parsed"].isna() | clean["incident_datetime_parsed"].isna() | (clean["first_assignment_datetime_parsed"] >= clean["incident_datetime_parsed"])
    clean["scene_after_call"] = clean["first_on_scene_datetime_parsed"].isna() | clean["incident_datetime_parsed"].isna() | (clean["first_on_scene_datetime_parsed"] >= clean["incident_datetime_parsed"])
    clean["hospital_after_scene"] = clean["first_hosp_arrival_datetime_parsed"].isna() | clean["first_on_scene_datetime_parsed"].isna() | (clean["first_hosp_arrival_datetime_parsed"] >= clean["first_on_scene_datetime_parsed"])
    clean["close_after_call"] = clean["incident_close_datetime_parsed"].isna() | clean["incident_datetime_parsed"].isna() | (clean["incident_close_datetime_parsed"] >= clean["incident_datetime_parsed"])
    if "dispatch_response_seconds_qy_num" in clean:
        computed_dispatch = (clean["first_assignment_datetime_parsed"] - clean["incident_datetime_parsed"]).dt.total_seconds()
        clean["dispatch_seconds_delta"] = (computed_dispatch - clean["dispatch_response_seconds_qy_num"]).abs()
    if "incident_response_seconds_qy_num" in clean:
        computed_response = (clean["first_on_scene_datetime_parsed"] - clean["incident_datetime_parsed"]).dt.total_seconds()
        clean["incident_seconds_delta"] = (computed_response - clean["incident_response_seconds_qy_num"]).abs()
    clean["demand_cohort"] = clean["has_valid_id"] & clean["has_valid_incident_datetime"] & ~clean["duplicate_incident_id"]
    clean["response_cohort"] = (
        clean["demand_cohort"]
        & (clean["valid_incident_rspns_time_indc_bool"] == True)
        & clean["incident_response_seconds_qy_num"].notna()
        & clean["incident_seconds_nonnegative"]
        & clean["scene_after_call"]
    )
    clean["transport_cohort"] = clean["response_cohort"] & clean["first_hosp_arrival_datetime_parsed"].notna() & clean["hospital_after_scene"]
    clean["special_event_cohort"] = clean["special_event_indicator_bool"] == True
    return clean


def write_parquet(frame, path):
    try:
        frame.to_parquet(path, index=False, engine="pyarrow", compression="snappy")
    except ImportError as error:
        raise PipelineError("Phase 3 requires pyarrow to write Parquet. Install pyarrow first.") from error


def value_counts(frame, field, limit=25):
    counts = frame[field].fillna("<missing>").value_counts(dropna=False).head(limit)
    return {str(index): int(value) for index, value in counts.items()}


def build_quality_report(raw, clean, manifest, config):
    pd = require_pandas()
    date_min = clean["incident_datetime_parsed"].min()
    date_max = clean["incident_datetime_parsed"].max()
    missing = {field: int(raw[field].isna().sum() + (raw[field].astype("string").str.strip() == "").fillna(False).sum()) for field in config["extraction"]["columns"]}
    return {
        "report_version": "1.0.0",
        "generated_at": utc_now(),
        "snapshot_id": manifest["snapshot_id"],
        "source_rows": int(len(raw)),
        "manifest_expected_rows": int(manifest["expected_rows"]),
        "date_min": None if pd.isna(date_min) else date_min.isoformat(),
        "date_max": None if pd.isna(date_max) else date_max.isoformat(),
        "missing_values": missing,
        "duplicate_rows_exact": int(clean["exact_duplicate"].sum()),
        "duplicate_incident_ids": int(clean["duplicate_incident_id"].sum()),
        "invalid_incident_datetime": int((~clean["has_valid_incident_datetime"]).sum()),
        "negative_dispatch_seconds": int((clean["dispatch_response_seconds_qy_num"] < 0).sum()),
        "negative_incident_response_seconds": int((clean["incident_response_seconds_qy_num"] < 0).sum()),
        "negative_travel_seconds": int((clean["incident_travel_tm_seconds_qy_num"] < 0).sum()),
        "sequence_violations": {
            "assignment_before_call": int((~clean["assignment_after_call"]).sum()),
            "scene_before_call": int((~clean["scene_after_call"]).sum()),
            "hospital_before_scene": int((~clean["hospital_after_scene"]).sum()),
            "close_before_call": int((~clean["close_after_call"]).sum()),
        },
        "category_profiles": {
            "borough": value_counts(clean, "borough_cohort"),
            "initial_call_type": value_counts(clean, "initial_call_type_norm"),
            "initial_severity_level_code": value_counts(clean, "initial_severity_level_code"),
            "valid_incident_rspns_time_indc": value_counts(clean, "valid_incident_rspns_time_indc"),
            "transfer_indicator": value_counts(clean, "transfer_indicator"),
        },
        "notes": [
            "Timestamps are treated as NYC local floating timestamps, as documented in the study plan.",
            "Missing flags are preserved as null; they are not converted to false.",
            "Demand and response cohorts are separate; response exclusions do not remove rows from demand.",
        ],
    }


def build_quarantine(clean):
    reasons = []
    checks = [
        ("missing_or_invalid_incident_id", ~clean["has_valid_id"]),
        ("invalid_incident_datetime", ~clean["has_valid_incident_datetime"]),
        ("duplicate_incident_id", clean["duplicate_incident_id"]),
        ("negative_dispatch_seconds", clean["dispatch_response_seconds_qy_num"] < 0),
        ("negative_incident_response_seconds", clean["incident_response_seconds_qy_num"] < 0),
        ("negative_travel_seconds", clean["incident_travel_tm_seconds_qy_num"] < 0),
        ("assignment_before_call", ~clean["assignment_after_call"]),
        ("scene_before_call", ~clean["scene_after_call"]),
        ("hospital_before_scene", ~clean["hospital_after_scene"]),
        ("close_before_call", ~clean["close_after_call"]),
    ]
    for reason, mask in checks:
        subset = clean.loc[mask.fillna(False), ["row_number", "incident_id", "incident_datetime", "borough"]].copy()
        subset["reason"] = reason
        reasons.append(subset)
    if not reasons:
        return clean.iloc[0:0][["row_number", "incident_id", "incident_datetime", "borough"]].assign(reason=[])
    pd = require_pandas()
    return pd.concat(reasons, ignore_index=True).drop_duplicates(["row_number", "reason"]).sort_values(["row_number", "reason"])


def build_cohort_summary(clean):
    source_rows = len(clean)
    demand = clean["demand_cohort"]
    response = clean["response_cohort"]
    transport = clean["transport_cohort"]
    special = clean["special_event_cohort"]
    return {
        "generated_at": utc_now(),
        "source_rows": int(source_rows),
        "demand_cohort_rows": int(demand.sum()),
        "response_cohort_rows": int(response.sum()),
        "transport_cohort_rows": int(transport.sum()),
        "special_event_rows": int(special.sum()),
        "excluded_from_demand": {
            "missing_or_invalid_id": int((~clean["has_valid_id"]).sum()),
            "invalid_incident_datetime": int((~clean["has_valid_incident_datetime"]).sum()),
            "duplicate_incident_id": int(clean["duplicate_incident_id"].sum()),
        },
        "excluded_from_response": {
            "not_in_demand_cohort": int((~demand).sum()),
            "invalid_official_response_flag": int((demand & (clean["valid_incident_rspns_time_indc_bool"] != True)).sum()),
            "missing_incident_response_seconds": int((demand & clean["incident_response_seconds_qy_num"].isna()).sum()),
            "negative_incident_response_seconds": int((demand & (clean["incident_response_seconds_qy_num"] < 0)).sum()),
            "scene_before_call": int((demand & ~clean["scene_after_call"]).sum()),
        },
        "borough_counts_demand": {str(key): int(value) for key, value in clean.loc[demand, "borough_cohort"].value_counts().sort_index().items()},
        "borough_counts_response": {str(key): int(value) for key, value in clean.loc[response, "borough_cohort"].value_counts().sort_index().items()},
    }


def phase3(folder, config):
    manifest, _ = load_snapshot(folder, config, strict=False)
    if manifest["status"] != "complete":
        raise PipelineError("Phase 3 requires a complete snapshot")
    verification = verify(folder, config)
    raw = dataframe_from_snapshot(folder, manifest, config)
    if len(raw) != manifest["expected_rows"]:
        raise PipelineError("Raw rows do not match manifest")
    clean = add_cleaning_columns(raw)
    interim = folder / "interim"
    processed = folder / "processed"
    interim.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    quality_report = build_quality_report(raw, clean, manifest, config)
    cohort_summary = build_cohort_summary(clean)
    quarantine = build_quarantine(clean)
    save_json(interim / "quality_report.json", json_safe(quality_report))
    save_json(processed / "cohort_summary.json", json_safe(cohort_summary))
    save_json(interim / "inclusion_exclusion_report.json", json_safe({
        "generated_at": utc_now(),
        "snapshot_id": manifest["snapshot_id"],
        "verification": verification,
        "cohorts": cohort_summary,
        "quarantine_rows": int(len(quarantine)),
    }))
    quarantine.to_csv(interim / "quarantine.csv", index=False)
    write_parquet(clean, processed / "incidents_clean.parquet")
    write_parquet(clean.loc[clean["demand_cohort"]].copy(), processed / "demand_cohort.parquet")
    write_parquet(clean.loc[clean["response_cohort"]].copy(), processed / "response_cohort.parquet")
    write_parquet(clean.loc[clean["transport_cohort"]].copy(), processed / "transport_cohort.parquet")
    result = {
        "snapshot_id": manifest["snapshot_id"],
        "source_rows": int(len(raw)),
        "quality_report": str((interim / "quality_report.json").relative_to(ROOT)),
        "cohort_summary": str((processed / "cohort_summary.json").relative_to(ROOT)),
        "quarantine": str((interim / "quarantine.csv").relative_to(ROOT)),
        "incidents_clean": str((processed / "incidents_clean.parquet").relative_to(ROOT)),
        "demand_cohort_rows": cohort_summary["demand_cohort_rows"],
        "response_cohort_rows": cohort_summary["response_cohort_rows"],
    }
    return result


def split_name(timestamp, forecast_config):
    for name in ("train", "validation", "test"):
        start = datetime.fromisoformat(forecast_config[name]["start_inclusive"])
        end = datetime.fromisoformat(forecast_config[name]["end_exclusive"])
        if start <= timestamp < end:
            return name
    return "outside"


def complete_hourly_index(config, zones):
    pd = require_pandas()
    start = pd.Timestamp(config["window"]["start_inclusive"])
    end = pd.Timestamp(config["window"]["end_exclusive"])
    hours = pd.date_range(start=start, end=end, freq="h", inclusive="left")
    return pd.MultiIndex.from_product([sorted(zones), hours], names=["zone_id", "hour_start"])


def build_hourly_panel(demand, config):
    pd = require_pandas()
    forecast = config["forecast"]
    geography = config["geography"]
    zone_field = "borough_cohort" if geography["forecast_unit"] == "borough" else geography["forecast_unit"]
    demand = demand.copy()
    demand["hour_start"] = demand["incident_datetime_parsed"].dt.floor("h")
    demand["zone_id"] = demand[zone_field].fillna(config["geography"]["unknown_zone_id"])
    observed_zones = sorted(demand["zone_id"].dropna().unique().tolist())
    grouped = demand.groupby(["zone_id", "hour_start"], observed=True).size().rename("demand_count").reset_index()
    panel = grouped.set_index(["zone_id", "hour_start"]).reindex(complete_hourly_index(config, observed_zones), fill_value=0).reset_index()
    panel["demand_count"] = panel["demand_count"].astype("int64")
    panel["hour"] = panel["hour_start"].dt.hour
    panel["day_of_week"] = panel["hour_start"].dt.dayofweek
    panel["day_of_month"] = panel["hour_start"].dt.day
    panel["month"] = panel["hour_start"].dt.month
    panel["is_weekend"] = panel["day_of_week"].isin([5, 6])
    panel["target_start"] = panel["hour_start"]
    panel["target_end"] = panel["hour_start"] + pd.Timedelta(minutes=forecast["horizon_minutes"])
    panel["target_demand_count"] = panel["demand_count"]
    panel = panel.sort_values(["zone_id", "hour_start"]).reset_index(drop=True)
    grouped_panel = panel.groupby("zone_id", group_keys=False)
    for lag in forecast["lag_hours"]:
        panel[f"lag_{lag}h"] = grouped_panel["demand_count"].shift(lag)
    for window in forecast["rolling_window_hours"]:
        panel[f"rolling_mean_{window}h"] = grouped_panel["demand_count"].transform(lambda series: series.shift(1).rolling(window, min_periods=1).mean())
        panel[f"rolling_sum_{window}h"] = grouped_panel["demand_count"].transform(lambda series: series.shift(1).rolling(window, min_periods=1).sum())
    panel["feature_ready"] = grouped_panel.cumcount() >= int(forecast["warmup_hours"])
    panel["split"] = panel["target_start"].map(lambda value: split_name(value.to_pydatetime(), forecast))
    panel["label_available"] = panel["target_end"] <= pd.Timestamp(config["window"]["end_exclusive"])
    if forecast.get("purge_labels_crossing_split_boundary", True):
        panel["label_available"] = panel["label_available"] & panel.apply(
            lambda row: split_name(row["target_start"].to_pydatetime(), forecast) == split_name((row["target_end"] - pd.Timedelta(seconds=1)).to_pydatetime(), forecast),
            axis=1,
        )
    for column in [col for col in panel.columns if col.startswith("lag_") or col.startswith("rolling_")]:
        panel[column] = panel[column].astype("float64")
    return panel


def build_feature_dictionary(config):
    forecast = config["forecast"]
    features = [
        {"name": "zone_id", "type": "categorical", "source": "borough_cohort", "leakage": "none"},
        {"name": "hour", "type": "calendar", "source": "target_start", "leakage": "none"},
        {"name": "day_of_week", "type": "calendar", "source": "target_start", "leakage": "none"},
        {"name": "is_weekend", "type": "calendar", "source": "target_start", "leakage": "none"},
    ]
    for lag in forecast["lag_hours"]:
        features.append({"name": f"lag_{lag}h", "type": "lag", "source": "past demand_count", "leakage": "past_only"})
    for window in forecast["rolling_window_hours"]:
        features.append({"name": f"rolling_mean_{window}h", "type": "rolling_mean", "source": "past demand_count", "leakage": "past_only"})
        features.append({"name": f"rolling_sum_{window}h", "type": "rolling_sum", "source": "past demand_count", "leakage": "past_only"})
    return {
        "generated_at": utc_now(),
        "target": forecast["target"],
        "horizon_minutes": forecast["horizon_minutes"],
        "frequency_minutes": forecast["frequency_minutes"],
        "warmup_hours": forecast["warmup_hours"],
        "features": features,
        "target_column": "target_demand_count",
        "split_column": "split",
        "feature_ready_column": "feature_ready",
        "notes": [
            "Lag and rolling features use only observations strictly before target_start.",
            "Rows before warmup_hours are preserved but marked feature_ready=false.",
            "Zero-filled hours rely on the verified continuous extraction coverage for the selected window.",
        ],
    }


def build_temporal_partitions(panel, config):
    result = {"generated_at": utc_now(), "splits": {}, "row_counts": {}}
    for name in ("train", "validation", "test"):
        start = config["forecast"][name]["start_inclusive"]
        end = config["forecast"][name]["end_exclusive"]
        subset = panel[panel["split"] == name]
        result["splits"][name] = {"start_inclusive": start, "end_exclusive": end}
        result["row_counts"][name] = {
            "rows": int(len(subset)),
            "feature_ready_rows": int(subset["feature_ready"].sum()),
            "label_available_rows": int(subset["label_available"].sum()),
            "model_ready_rows": int((subset["feature_ready"] & subset["label_available"]).sum()),
        }
    result["row_counts"]["outside"] = {"rows": int((panel["split"] == "outside").sum())}
    return result


def build_geography_summary(panel, demand, response, config):
    zone_counts = panel.groupby("zone_id", observed=True)["demand_count"].sum().sort_index()
    response_counts = response.groupby("borough_cohort", observed=True).size().sort_index()
    return {
        "generated_at": utc_now(),
        "forecast_unit": config["geography"]["forecast_unit"],
        "simulation_unit_target": config["geography"]["simulation_unit_target"],
        "coordinates_status": config["geography"]["coordinates"],
        "socioeconomic_quintiles_status": config["geography"]["socioeconomic_quintiles"],
        "zones": {
            str(zone): {
                "demand_count": int(count),
                "response_count": int(response_counts.get(zone, 0)),
                "panel_hours": int((panel["zone_id"] == zone).sum()),
            }
            for zone, count in zone_counts.items()
        },
    }


def build_simulation_events(clean, config):
    pd = require_pandas()
    start = pd.Timestamp(config["window"]["start_inclusive"])
    columns = [
        "incident_id",
        "incident_datetime_parsed",
        "borough_cohort",
        "incident_dispatch_area_norm",
        "initial_call_type_norm",
        "initial_severity_level_code_num",
        "valid_incident_rspns_time_indc_bool",
        "incident_response_seconds_qy_num",
        "dispatch_response_seconds_qy_num",
        "incident_travel_tm_seconds_qy_num",
        "response_cohort",
        "transport_cohort",
        "special_event_cohort",
    ]
    available = [column for column in columns if column in clean.columns]
    events = clean[available].copy()
    events["sim_time_min"] = (events["incident_datetime_parsed"] - start).dt.total_seconds() / 60
    events = events.sort_values(["incident_datetime_parsed", "incident_id"]).reset_index(drop=True)
    events["event_sequence"] = range(1, len(events) + 1)
    return events


def phase4(folder, config):
    manifest, _ = load_snapshot(folder, config, strict=False)
    if manifest["status"] != "complete":
        raise PipelineError("Phase 4 requires a complete snapshot")
    processed = folder / "processed"
    simulation = folder / "simulation"
    incidents_path = processed / "incidents_clean.parquet"
    demand_path = processed / "demand_cohort.parquet"
    response_path = processed / "response_cohort.parquet"
    if not incidents_path.exists() or not demand_path.exists() or not response_path.exists():
        raise PipelineError("Phase 4 requires phase3 outputs; run phase3 first")
    pd = require_pandas()
    clean = pd.read_parquet(incidents_path)
    demand = pd.read_parquet(demand_path)
    response = pd.read_parquet(response_path)
    panel = build_hourly_panel(demand, config)
    feature_dictionary = build_feature_dictionary(config)
    temporal_partitions = build_temporal_partitions(panel, config)
    geography_summary = build_geography_summary(panel, demand, response, config)
    simulation_events = build_simulation_events(clean, config)
    processed.mkdir(parents=True, exist_ok=True)
    simulation.mkdir(parents=True, exist_ok=True)
    write_parquet(panel, processed / "hourly_demand_panel.parquet")
    write_parquet(panel[panel["feature_ready"] & panel["label_available"]].copy(), processed / "model_ready_hourly_demand_panel.parquet")
    write_parquet(simulation_events, simulation / "historical_incident_events.parquet")
    save_json(processed / "feature_dictionary.json", json_safe(feature_dictionary))
    save_json(processed / "temporal_partitions.json", json_safe(temporal_partitions))
    save_json(processed / "geography_summary.json", json_safe(geography_summary))
    return {
        "snapshot_id": manifest["snapshot_id"],
        "panel_rows": int(len(panel)),
        "model_ready_rows": int((panel["feature_ready"] & panel["label_available"]).sum()),
        "zones": int(panel["zone_id"].nunique()),
        "simulation_events": int(len(simulation_events)),
        "hourly_panel": str((processed / "hourly_demand_panel.parquet").relative_to(ROOT)),
        "model_ready_panel": str((processed / "model_ready_hourly_demand_panel.parquet").relative_to(ROOT)),
        "simulation_events_path": str((simulation / "historical_incident_events.parquet").relative_to(ROOT)),
        "temporal_partitions": str((processed / "temporal_partitions.json").relative_to(ROOT)),
        "feature_dictionary": str((processed / "feature_dictionary.json").relative_to(ROOT)),
        "geography_summary": str((processed / "geography_summary.json").relative_to(ROOT)),
    }


def require_sklearn():
    try:
        import joblib
        from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    except ImportError as error:
        raise PipelineError("Phase 5 requires scikit-learn and joblib. Install research dependencies first.") from error
    return joblib, RandomForestRegressor, HistGradientBoostingRegressor


def phase5_feature_columns(config):
    forecast = config["forecast"]
    columns = ["zone_id", "hour", "day_of_week", "day_of_month", "month", "is_weekend"]
    columns.extend(f"lag_{lag}h" for lag in forecast["lag_hours"])
    for window in forecast["rolling_window_hours"]:
        columns.extend([f"rolling_mean_{window}h", f"rolling_sum_{window}h"])
    return columns


def model_matrix(frame, feature_columns, trained_columns=None):
    pd = require_pandas()
    numeric = [column for column in feature_columns if column != "zone_id"]
    data = frame[feature_columns].copy()
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0).astype("float64")
    data["zone_id"] = data["zone_id"].fillna("UNKNOWN").astype("string")
    matrix = pd.concat(
        [data[numeric].reset_index(drop=True), pd.get_dummies(data["zone_id"], prefix="zone", dtype="float64").reset_index(drop=True)],
        axis=1,
    )
    if trained_columns is None:
        return matrix, list(matrix.columns)
    for column in trained_columns:
        if column not in matrix:
            matrix[column] = 0.0
    return matrix[trained_columns], trained_columns


def fit_temporal_baseline(train):
    target = "target_demand_count"
    return {
        "model_id": "baseline_temporal_v1",
        "family": "baseline_temporal",
        "description": "Mean demand by zone, day of week and hour, with zone-hour, zone and global fallbacks.",
        "primary": train.groupby(["zone_id", "day_of_week", "hour"], observed=True)[target].mean().reset_index(name="prediction"),
        "zone_hour": train.groupby(["zone_id", "hour"], observed=True)[target].mean().reset_index(name="prediction"),
        "zone": train.groupby(["zone_id"], observed=True)[target].mean().reset_index(name="prediction"),
        "global": float(train[target].mean()),
    }


def predict_temporal_baseline(model, frame):
    prediction = frame[["zone_id", "day_of_week", "hour"]].merge(
        model["primary"], on=["zone_id", "day_of_week", "hour"], how="left"
    )["prediction"]
    fallback = frame[["zone_id", "hour"]].merge(model["zone_hour"], on=["zone_id", "hour"], how="left")["prediction"]
    prediction = prediction.fillna(fallback)
    fallback = frame[["zone_id"]].merge(model["zone"], on=["zone_id"], how="left")["prediction"]
    return prediction.fillna(fallback).fillna(model["global"]).clip(lower=0)


def regression_metrics(frame):
    errors = frame["prediction"] - frame["actual"]
    absolute = errors.abs()
    squared = errors.pow(2)
    denominator = frame["actual"].sum()
    return {
        "rows": int(len(frame)),
        "mae": float(absolute.mean()),
        "rmse": float(math.sqrt(squared.mean())),
        "wape": None if denominator == 0 else float(absolute.sum() / denominator),
        "bias": float(errors.mean()),
        "actual_sum": float(denominator),
        "prediction_sum": float(frame["prediction"].sum()),
    }


def evaluate_forecasts(predictions):
    metrics = {"global": {}, "by_zone": {}}
    for (model_id, split), subset in predictions.groupby(["model_id", "split"], observed=True):
        metrics["global"].setdefault(str(model_id), {})[str(split)] = regression_metrics(subset)
    for (model_id, split, zone), subset in predictions.groupby(["model_id", "split", "zone_id"], observed=True):
        metrics["by_zone"].setdefault(str(model_id), {}).setdefault(str(split), {})[str(zone)] = regression_metrics(subset)
    validation_scores = {
        model_id: values["validation"]["mae"]
        for model_id, values in metrics["global"].items()
        if "validation" in values
    }
    metrics["selection"] = {
        "criterion": "lowest validation MAE",
        "best_model_id": min(validation_scores, key=validation_scores.get) if validation_scores else None,
        "validation_mae": validation_scores,
    }
    return metrics


def build_forecast_rows(model_id, model_family, frame, predictions, config):
    pd = require_pandas()
    result = frame[["target_start", "target_end", "zone_id", "split", "target_demand_count"]].copy().reset_index(drop=True)
    predicted = pd.Series(predictions).reset_index(drop=True).astype("float64").clip(lower=0)
    if predicted.isna().any():
        raise PipelineError(f"{model_id} produced missing predictions")
    result["model_id"] = model_id
    result["model_family"] = model_family
    result["issued_at"] = result["target_start"]
    result["training_window_end"] = config["forecast"]["train"]["end_exclusive"]
    result["actual"] = result["target_demand_count"].astype("float64")
    result["prediction"] = predicted
    return result[[
        "model_id", "model_family", "issued_at", "training_window_end", "target_start",
        "target_end", "zone_id", "split", "actual", "prediction",
    ]]


def build_model_card(manifest, config, feature_columns, trained_columns, metrics, model_specs):
    return {
        "generated_at": utc_now(),
        "snapshot_id": manifest["snapshot_id"],
        "study_id": config["study_id"],
        "target": config["forecast"]["target"],
        "horizon_minutes": config["forecast"]["horizon_minutes"],
        "training_window": config["forecast"]["train"],
        "validation_window": config["forecast"]["validation"],
        "test_window": config["forecast"]["test"],
        "models_compared": model_specs,
        "input_features": feature_columns,
        "encoded_feature_columns": trained_columns,
        "metrics": metrics,
        "limitations": [
            "Models estimate hourly borough demand, not ambulance travel time or resource availability.",
            "The fixed models are trained only with the training split; validation is used for model comparison.",
            "Predictions are retrospective and suitable for historical simulation integration, not live inference yet.",
        ],
    }


def phase5(folder, config):
    manifest, _ = load_snapshot(folder, config, strict=False)
    if manifest["status"] != "complete":
        raise PipelineError("Phase 5 requires a complete snapshot")
    processed = folder / "processed"
    panel_path = processed / "model_ready_hourly_demand_panel.parquet"
    if not panel_path.exists():
        raise PipelineError("Phase 5 requires phase4 outputs; run phase4 first")
    pd = require_pandas()
    joblib, RandomForestRegressor, HistGradientBoostingRegressor = require_sklearn()
    panel = pd.read_parquet(panel_path).sort_values(["zone_id", "target_start"]).reset_index(drop=True)
    train = panel[panel["split"] == "train"].copy()
    evaluation = panel[panel["split"].isin(["validation", "test"])].copy()
    if train.empty or evaluation.empty:
        raise PipelineError("Phase 5 requires non-empty train and validation/test rows")
    feature_columns = phase5_feature_columns(config)
    missing = [column for column in feature_columns + ["target_demand_count", "split"] if column not in panel.columns]
    if missing:
        raise PipelineError(f"Phase 5 missing required columns: {', '.join(missing)}")
    seeds = config["evaluation"]["seeds"]
    baseline = fit_temporal_baseline(train)
    train_matrix, trained_columns = model_matrix(train, feature_columns)
    eval_matrix, _ = model_matrix(evaluation, feature_columns, trained_columns)
    target = train["target_demand_count"].astype("float64")
    models = {
        "random_forest_v1": RandomForestRegressor(
            n_estimators=180,
            max_depth=18,
            min_samples_leaf=3,
            random_state=int(seeds["model"]),
            n_jobs=-1,
        ),
        "hist_gradient_boosting_v1": HistGradientBoostingRegressor(
            max_iter=260,
            learning_rate=0.06,
            max_leaf_nodes=31,
            l2_regularization=0.05,
            random_state=int(seeds["model"]),
        ),
    }
    for model in models.values():
        model.fit(train_matrix, target)
    forecast_frames = [
        build_forecast_rows("baseline_temporal_v1", "baseline_temporal", evaluation, predict_temporal_baseline(baseline, evaluation), config)
    ]
    for model_id, model in models.items():
        forecast_frames.append(build_forecast_rows(model_id, model.__class__.__name__, evaluation, pd.Series(model.predict(eval_matrix), index=evaluation.index), config))
    predictions = pd.concat(forecast_frames, ignore_index=True).sort_values(["model_id", "target_start", "zone_id"]).reset_index(drop=True)
    metrics = evaluate_forecasts(predictions)
    model_specs = [
        {"model_id": "baseline_temporal_v1", "family": "baseline_temporal"},
        {"model_id": "random_forest_v1", "family": "RandomForestRegressor"},
        {"model_id": "hist_gradient_boosting_v1", "family": "HistGradientBoostingRegressor"},
    ]
    model_card = build_model_card(manifest, config, feature_columns, trained_columns, metrics, model_specs)
    artifact_root = repository_path(config["paths"]["models_root"]) / manifest["snapshot_id"] / "phase5"
    models_dir = artifact_root / "models"
    predictions_dir = artifact_root / "predictions"
    reports_dir = artifact_root / "reports"
    models_dir.mkdir(parents=True, exist_ok=True)
    predictions_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": baseline, "feature_columns": feature_columns}, models_dir / "baseline_temporal_v1.joblib")
    for model_id, model in models.items():
        joblib.dump({"model": model, "feature_columns": feature_columns, "trained_columns": trained_columns}, models_dir / f"{model_id}.joblib")
    write_parquet(predictions, predictions_dir / "retrospective_forecasts.parquet")
    write_parquet(predictions, processed / "retrospective_forecasts.parquet")
    save_json(reports_dir / "metrics.json", json_safe(metrics))
    save_json(reports_dir / "model_card.json", json_safe(model_card))
    return {
        "snapshot_id": manifest["snapshot_id"],
        "models_compared": len(model_specs),
        "best_model_id": metrics["selection"]["best_model_id"],
        "prediction_rows": int(len(predictions)),
        "metrics": str((reports_dir / "metrics.json").relative_to(ROOT)),
        "model_card": str((reports_dir / "model_card.json").relative_to(ROOT)),
        "predictions": str((predictions_dir / "retrospective_forecasts.parquet").relative_to(ROOT)),
        "api_ready_predictions": str((processed / "retrospective_forecasts.parquet").relative_to(ROOT)),
    }


NYC_BOROUGH_SCENARIO = {
    "BRONX": {"id": 1, "name": "Bronx", "code": "BRONX", "centroid": [40.8448, -73.8648], "quintile_proxy": 1},
    "BROOKLYN": {"id": 2, "name": "Brooklyn", "code": "BROOKLYN", "centroid": [40.6782, -73.9442], "quintile_proxy": 2},
    "MANHATTAN": {"id": 3, "name": "Manhattan", "code": "MANHATTAN", "centroid": [40.7831, -73.9712], "quintile_proxy": 4},
    "QUEENS": {"id": 4, "name": "Queens", "code": "QUEENS", "centroid": [40.7282, -73.7949], "quintile_proxy": 3},
    "RICHMOND / STATEN ISLAND": {"id": 5, "name": "Staten Island", "code": "STATEN_ISLAND", "centroid": [40.5795, -74.1502], "quintile_proxy": 5},
    "UNKNOWN": {"id": 99, "name": "Unknown NYC", "code": "UNKNOWN", "centroid": [40.7128, -74.0060], "quintile_proxy": 3},
}


def borough_meta(zone):
    return NYC_BOROUGH_SCENARIO.get(str(zone), NYC_BOROUGH_SCENARIO["UNKNOWN"])


def deterministic_jitter(value, scale):
    token = digest(str(value).encode("utf-8"))
    raw = int(token[:8], 16) / 0xFFFFFFFF
    return (raw - 0.5) * scale


def approximate_latitude(row):
    meta = borough_meta(row["borough_cohort"])
    return round(meta["centroid"][0] + deterministic_jitter(str(row["incident_id"]) + ":lat", 0.045), 6)


def approximate_longitude(row):
    meta = borough_meta(row["borough_cohort"])
    return round(meta["centroid"][1] + deterministic_jitter(str(row["incident_id"]) + ":lng", 0.060), 6)


def map_priority(severity):
    try:
        value = float(severity)
    except (TypeError, ValueError):
        return "media"
    if value <= 3:
        return "alta"
    if value <= 5:
        return "media"
    return "baja"


def map_incident_type(call_type):
    text = normalize_text(call_type) or ""
    if any(token in text for token in ("CARD", "ARREST", "HEART")):
        return "emergencia cardiaca"
    if any(token in text for token in ("RESP", "ASTHMA", "BREATH")):
        return "emergencia respiratoria"
    if any(token in text for token in ("MVA", "CAR", "VEH", "TRAFFIC")):
        return "accidente de transito"
    if any(token in text for token in ("INJ", "TRAUMA", "SHOT", "STAB")):
        return "trauma"
    if any(token in text for token in ("FALL", "EDP")):
        return "caida"
    return "otro"


def minutes_between(frame, end_column, start_column):
    return (frame[end_column] - frame[start_column]).dt.total_seconds() / 60


def valid_positive(series):
    return series.where(series.notna() & (series >= 0))


def summarize_numeric(series):
    pd = require_pandas()
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"count": 0, "mean": None, "median": None, "p75": None, "p90": None, "p95": None, "max": None}
    return {
        "count": int(clean.count()),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p75": float(clean.quantile(0.75)),
        "p90": float(clean.quantile(0.90)),
        "p95": float(clean.quantile(0.95)),
        "max": float(clean.max()),
    }


def build_time_components(clean):
    components = clean[[
        "incident_id",
        "incident_datetime_parsed",
        "borough_cohort",
        "incident_dispatch_area_norm",
        "response_cohort",
        "transport_cohort",
        "dispatch_response_seconds_qy_num",
        "incident_response_seconds_qy_num",
        "incident_travel_tm_seconds_qy_num",
        "first_on_scene_datetime_parsed",
        "first_to_hosp_datetime_parsed",
        "first_hosp_arrival_datetime_parsed",
        "incident_close_datetime_parsed",
    ]].copy()
    components["observed_dispatch_min"] = valid_positive(components["dispatch_response_seconds_qy_num"] / 60)
    components["observed_response_min"] = valid_positive(components["incident_response_seconds_qy_num"] / 60)
    components["observed_assignment_to_scene_min"] = valid_positive(components["incident_travel_tm_seconds_qy_num"] / 60)
    components["observed_scene_to_departure_min"] = valid_positive(minutes_between(components, "first_to_hosp_datetime_parsed", "first_on_scene_datetime_parsed"))
    components["observed_transport_to_hospital_min"] = valid_positive(minutes_between(components, "first_hosp_arrival_datetime_parsed", "first_to_hosp_datetime_parsed"))
    components["observed_call_to_close_min"] = valid_positive(minutes_between(components, "incident_close_datetime_parsed", "incident_datetime_parsed"))
    return components[[
        "incident_id",
        "incident_datetime_parsed",
        "borough_cohort",
        "incident_dispatch_area_norm",
        "response_cohort",
        "transport_cohort",
        "observed_dispatch_min",
        "observed_response_min",
        "observed_assignment_to_scene_min",
        "observed_scene_to_departure_min",
        "observed_transport_to_hospital_min",
        "observed_call_to_close_min",
    ]]


def build_historical_replay_inputs(clean, components, config):
    pd = require_pandas()
    start = pd.Timestamp(config["window"]["start_inclusive"])
    base = clean.loc[clean["demand_cohort"]].copy()
    base["sim_time_min"] = (base["incident_datetime_parsed"] - start).dt.total_seconds() / 60
    base["zone_id"] = base["borough_cohort"].map(lambda value: borough_meta(value)["id"])
    base["zone_code"] = base["borough_cohort"].map(lambda value: borough_meta(value)["code"])
    base["zone_name"] = base["borough_cohort"].map(lambda value: borough_meta(value)["name"])
    base["quintile_proxy"] = base["borough_cohort"].map(lambda value: borough_meta(value)["quintile_proxy"])
    base["latitud"] = [
        round(borough_meta(zone)["centroid"][0] + deterministic_jitter(str(incident_id) + ":lat", 0.045), 6)
        for incident_id, zone in zip(base["incident_id"], base["borough_cohort"])
    ]
    base["longitud"] = [
        round(borough_meta(zone)["centroid"][1] + deterministic_jitter(str(incident_id) + ":lng", 0.060), 6)
        for incident_id, zone in zip(base["incident_id"], base["borough_cohort"])
    ]
    base["coordinate_status"] = "synthetic_jittered_borough_centroid_not_real_gps"
    base["prioridad"] = base["initial_severity_level_code_num"].map(map_priority)
    base["tipo"] = base["initial_call_type_norm"].map(map_incident_type)
    base["requiere_traslado"] = base["transport_cohort"].fillna(False).astype(bool)
    merged = base.merge(
        components[[
            "incident_id",
            "observed_dispatch_min",
            "observed_response_min",
            "observed_assignment_to_scene_min",
            "observed_scene_to_departure_min",
            "observed_transport_to_hospital_min",
            "observed_call_to_close_min",
        ]],
        on="incident_id",
        how="left",
    )
    return merged[[
        "incident_id",
        "incident_datetime_parsed",
        "sim_time_min",
        "zone_id",
        "zone_code",
        "zone_name",
        "borough_cohort",
        "incident_dispatch_area_norm",
        "zipcode_norm",
        "latitud",
        "longitud",
        "coordinate_status",
        "quintile_proxy",
        "prioridad",
        "tipo",
        "initial_call_type_norm",
        "initial_severity_level_code_num",
        "requiere_traslado",
        "response_cohort",
        "transport_cohort",
        "observed_dispatch_min",
        "observed_response_min",
        "observed_assignment_to_scene_min",
        "observed_scene_to_departure_min",
        "observed_transport_to_hospital_min",
        "observed_call_to_close_min",
    ]].sort_values(["sim_time_min", "incident_id"]).reset_index(drop=True)


def hourly_total_demand(panel):
    return panel.groupby("hour_start", observed=True)["demand_count"].sum()


def build_calibration_parameters(clean, panel, components, config):
    demand = clean.loc[clean["demand_cohort"]]
    response = clean.loc[clean["response_cohort"]]
    transport = clean.loc[clean["transport_cohort"]]
    total_hourly = hourly_total_demand(panel)
    mean_service = summarize_numeric(components["observed_call_to_close_min"])
    median_service_min = mean_service["median"] or summarize_numeric(components["observed_response_min"])["median"] or 45.0
    peak_hourly_p90 = float(total_hourly.quantile(0.90))
    resource_estimates = {}
    for utilization in (0.35, 0.50, 0.65):
        resource_estimates[f"target_utilization_{utilization:.2f}"] = int(math.ceil((peak_hourly_p90 * (median_service_min / 60)) / utilization))
    by_zone = {}
    for zone, subset in clean.groupby("borough_cohort", observed=True):
        zone_components = components[components["borough_cohort"] == zone]
        zone_demand = subset[subset["demand_cohort"]]
        zone_response = subset[subset["response_cohort"]]
        zone_transport = subset[subset["transport_cohort"]]
        zone_panel = panel[panel["zone_id"] == zone]
        by_zone[str(zone)] = {
            "demand_count": int(len(zone_demand)),
            "response_count": int(len(zone_response)),
            "transport_count": int(len(zone_transport)),
            "valid_response_rate": None if len(zone_demand) == 0 else float(len(zone_response) / len(zone_demand)),
            "transport_rate_among_response": None if len(zone_response) == 0 else float(len(zone_transport) / len(zone_response)),
            "hourly_demand": summarize_numeric(zone_panel["demand_count"]),
            "response_min": summarize_numeric(zone_components["observed_response_min"]),
            "dispatch_min": summarize_numeric(zone_components["observed_dispatch_min"]),
            "assignment_to_scene_min": summarize_numeric(zone_components["observed_assignment_to_scene_min"]),
            "scene_to_departure_min": summarize_numeric(zone_components["observed_scene_to_departure_min"]),
            "transport_to_hospital_min": summarize_numeric(zone_components["observed_transport_to_hospital_min"]),
            "call_to_close_min": summarize_numeric(zone_components["observed_call_to_close_min"]),
        }
    return {
        "generated_at": utc_now(),
        "snapshot_id": config["paths"].get("snapshot_id", "from_manifest"),
        "study_id": config["study_id"],
        "window": {
            "start_inclusive": config["window"]["start_inclusive"],
            "end_exclusive": config["window"]["end_exclusive"],
        },
        "global": {
            "demand_count": int(len(demand)),
            "response_count": int(len(response)),
            "transport_count": int(len(transport)),
            "valid_response_rate": float(len(response) / len(demand)) if len(demand) else None,
            "transport_rate_among_response": float(len(transport) / len(response)) if len(response) else None,
            "hourly_total_demand": summarize_numeric(total_hourly),
            "response_min": summarize_numeric(components["observed_response_min"]),
            "dispatch_min": summarize_numeric(components["observed_dispatch_min"]),
            "assignment_to_scene_min": summarize_numeric(components["observed_assignment_to_scene_min"]),
            "scene_to_departure_min": summarize_numeric(components["observed_scene_to_departure_min"]),
            "transport_to_hospital_min": summarize_numeric(components["observed_transport_to_hospital_min"]),
            "call_to_close_min": mean_service,
        },
        "by_zone": by_zone,
        "resource_estimates": {
            "basis": "Little-law-style rough capacity proxy using p90 total hourly demand and median call-to-close time; not observed FDNY fleet size.",
            "peak_hourly_demand_p90": peak_hourly_p90,
            "median_service_proxy_min": float(median_service_min),
            "ambulances_by_target_utilization": resource_estimates,
        },
    }


def build_nyc_scenario(calibration):
    zones = []
    bases = []
    hospitals = []
    for key, meta in NYC_BOROUGH_SCENARIO.items():
        if key == "UNKNOWN":
            continue
        lat, lng = meta["centroid"]
        zone_metrics = calibration["by_zone"].get(key, {})
        demand_daily = (zone_metrics.get("demand_count", 0) / 91) if zone_metrics else 0
        zones.append({
            "id": meta["id"],
            "nombre": meta["name"],
            "codigo": meta["code"],
            "centroide": [lat, lng],
            "poligono": [
                [round(lat + 0.055, 6), round(lng - 0.070, 6)],
                [round(lat + 0.055, 6), round(lng + 0.070, 6)],
                [round(lat - 0.055, 6), round(lng + 0.070, 6)],
                [round(lat - 0.055, 6), round(lng - 0.070, 6)],
            ],
            "quintil_socioeconomico_proxy": meta["quintile_proxy"],
            "demanda_historica_diaria": float(demand_daily),
            "geometry_status": "approximate_bbox_for_visualization_not_official_boundary",
        })
        bases.append({
            "id": meta["id"],
            "nombre": f"EMS staging proxy - {meta['name']}",
            "codigo": f"NYC-BASE-{meta['id']}",
            "latitud": lat,
            "longitud": lng,
            "zona_id": meta["id"],
            "capacidad_status": "proxy_pending_real_resource_data",
        })
        hospitals.append({
            "id": meta["id"],
            "nombre": f"Hospital proxy - {meta['name']}",
            "codigo": f"NYC-HOSP-{meta['id']}",
            "latitud": lat,
            "longitud": lng,
            "zona_id": meta["id"],
            "status": "placeholder_pending_versioned_hospital_source",
        })
    return {
        "scenario_id": "nyc_ems_historical_replay_v1",
        "generated_at": utc_now(),
        "city": "New York City",
        "source_snapshot": "20260909T040537085584Z-56d48fe7ce9b",
        "zones": zones,
        "bases": bases,
        "hospitals": hospitals,
        "notes": [
            "Borough centroids and bounding boxes are visualization proxies, not GPS incident locations.",
            "Actual ambulance bases, units and hospital capacities are not identifiable from NYC EMS Incident Dispatch Data.",
        ],
    }


def build_resource_assumptions(calibration):
    return {
        "generated_at": utc_now(),
        "status": "explicit_proxy_assumptions",
        "not_observed_in_dataset": [
            "ambulance fleet size",
            "ambulance starting positions",
            "ambulance availability schedules",
            "hospital capacities and handoff delay",
            "road-network travel times",
        ],
        "resource_estimates": calibration["resource_estimates"],
        "recommended_starting_point": {
            "fleet_size_proxy": calibration["resource_estimates"]["ambulances_by_target_utilization"]["target_utilization_0.50"],
            "use": "sensitivity baseline only; compare multiple fleet sizes in later experiments",
        },
        "counterfactual_policy_status": "requires_phase7_runtime_adapter_and_phase8_experimental_design",
    }


def phase6(folder, config):
    manifest, _ = load_snapshot(folder, config, strict=False)
    if manifest["status"] != "complete":
        raise PipelineError("Phase 6 requires a complete snapshot")
    processed = folder / "processed"
    simulation = folder / "simulation"
    required = {
        "incidents": processed / "incidents_clean.parquet",
        "panel": processed / "hourly_demand_panel.parquet",
        "predictions": processed / "retrospective_forecasts.parquet",
        "events": simulation / "historical_incident_events.parquet",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise PipelineError(f"Phase 6 requires previous outputs; missing: {', '.join(missing)}")
    pd = require_pandas()
    clean = pd.read_parquet(required["incidents"])
    panel = pd.read_parquet(required["panel"])
    predictions = pd.read_parquet(required["predictions"])
    components = build_time_components(clean)
    replay_inputs = build_historical_replay_inputs(clean, components, config)
    calibration = build_calibration_parameters(clean, panel, components, config)
    calibration["snapshot_id"] = manifest["snapshot_id"]
    scenario = build_nyc_scenario(calibration)
    scenario["source_snapshot"] = manifest["snapshot_id"]
    resource_assumptions = build_resource_assumptions(calibration)
    phase6_manifest = {
        "generated_at": utc_now(),
        "snapshot_id": manifest["snapshot_id"],
        "historical_arrivals": int(len(replay_inputs)),
        "observed_response_rows": int(components["observed_response_min"].notna().sum()),
        "prediction_models_available": sorted(predictions["model_id"].dropna().unique().tolist()),
        "outputs": {
            "historical_replay_inputs": "simulation/historical_replay_inputs.parquet",
            "observed_time_components": "simulation/observed_time_components.parquet",
            "calibration_parameters": "simulation/calibration_parameters.json",
            "nyc_scenario": "simulation/nyc_scenario.json",
            "resource_assumptions": "simulation/resource_assumptions.json",
        },
    }
    simulation.mkdir(parents=True, exist_ok=True)
    write_parquet(replay_inputs, simulation / "historical_replay_inputs.parquet")
    write_parquet(components, simulation / "observed_time_components.parquet")
    save_json(simulation / "calibration_parameters.json", json_safe(calibration))
    save_json(simulation / "nyc_scenario.json", json_safe(scenario))
    save_json(simulation / "resource_assumptions.json", json_safe(resource_assumptions))
    save_json(simulation / "phase6_manifest.json", json_safe(phase6_manifest))
    return {
        "snapshot_id": manifest["snapshot_id"],
        "historical_arrivals": int(len(replay_inputs)),
        "observed_response_rows": int(components["observed_response_min"].notna().sum()),
        "fleet_size_proxy": resource_assumptions["recommended_starting_point"]["fleet_size_proxy"],
        "historical_replay_inputs": str((simulation / "historical_replay_inputs.parquet").relative_to(ROOT)),
        "calibration_parameters": str((simulation / "calibration_parameters.json").relative_to(ROOT)),
        "nyc_scenario": str((simulation / "nyc_scenario.json").relative_to(ROOT)),
        "resource_assumptions": str((simulation / "resource_assumptions.json").relative_to(ROOT)),
    }


def extract(client, config, folder, max_pages=None):
    started = time.perf_counter()
    manifest, original = load_snapshot(folder, config)
    local = inspect_pages(folder, manifest, config)
    before = discover(client, config, manifest["mode"])
    if evidence_signature(before) != evidence_signature(original):
        manifest["status"] = "invalidated"
        save_json(folder / "source_changed.json", before)
        save_json(folder / "manifest.json", manifest)
        raise PipelineError("Source changed since snapshot creation; start a new snapshot")
    downloaded = 0
    download_seconds = 0.0
    total = local["rows"]
    initial_offset = total
    manifest["status"] = "extracting"
    save_json(folder / "manifest.json", manifest)
    while total < manifest["expected_rows"] and (max_pages is None or downloaded < max_pages):
        part, offset = page_position(manifest, total)
        start, end = part["start_inclusive"], part["end_exclusive"]
        query = {
            "$select": ",".join(config["extraction"]["columns"]),
            "$where": date_filter(start, end),
            "$order": ",".join(config["extraction"]["order_by"]),
            "$limit": config["extraction"]["page_size"], "$offset": offset,
        }
        page_start = time.perf_counter()
        rows, raw, url = client.query(query)
        elapsed = time.perf_counter() - page_start
        expected = min(config["extraction"]["page_size"], part["expected_rows"] - offset)
        if len(rows) != expected:
            raise PipelineError("Unexpected page length; source may have changed, rerun discovery")
        compressed = gzip.compress(raw, mtime=0)
        relative = f"raw/{start[:7]}/page-{offset:09d}.json.gz"
        atomic_write(folder / relative, compressed)
        manifest["pages"].append({
            "path": relative, "offset": offset, "rows": len(rows), "query": url,
            "sha256": digest(compressed), "raw_sha256": digest(raw),
            "compressed_bytes": len(compressed), "raw_bytes": len(raw),
            "download_seconds": elapsed, "downloaded_at": utc_now(),
        })
        save_json(folder / "manifest.json", manifest)
        total += len(rows)
        downloaded += 1
        download_seconds += elapsed
        print(f"Saved {relative}: {total}/{manifest['expected_rows']} rows", flush=True)
        del rows, raw, compressed
    summary = inspect_pages(folder, manifest, config)
    after = discover(client, config, manifest["mode"])
    if evidence_signature(after) != evidence_signature(original):
        manifest["status"] = "invalidated"
        save_json(folder / "source_changed.json", after)
        save_json(folder / "manifest.json", manifest)
        raise PipelineError("Source changed during extraction; snapshot invalidated")
    save_json(folder / "discovery_after.json", after)
    manifest["discovery_after_sha256"] = digest((folder / "discovery_after.json").read_bytes())
    complete = summary["rows"] == manifest["expected_rows"]
    if complete:
        start, end = selected_window(config, manifest["mode"])
        expected_days = {row["day"][:10]: int(row["incidents"]) for row in original["days"]["rows"] if start[:10] <= row["day"][:10] < end[:10]}
        if summary["daily_counts"] != expected_days:
            raise PipelineError("Downloaded daily counts differ from discovery")
    manifest["status"] = "complete" if complete else "paused"
    manifest["sessions"].append({
        "finished_at": utc_now(), "resumed_at_offset": initial_offset, "pages_downloaded": downloaded,
        "elapsed_seconds": time.perf_counter() - started, "page_download_seconds": download_seconds,
        "http_attempts_in_process": client.requests, "response_bytes_in_process": client.response_bytes,
        "python_peak_traced_bytes_in_process": tracemalloc.get_traced_memory()[1],
    })
    manifest["summary"] = summary
    study_rows = sum(int(row["incidents"]) for row in original["months"]["rows"])
    manifest["quarter_estimate"] = {
        "reference_rows": study_rows,
        "compressed_bytes": round(summary["compressed_bytes"] / summary["rows"] * study_rows),
        "raw_bytes": round(summary["raw_bytes"] / summary["rows"] * study_rows),
        "page_download_seconds": sum(page["download_seconds"] for page in manifest["pages"]) / summary["rows"] * study_rows,
        "basis": "linear pilot extrapolation; excludes discovery, retries and processing; not a guarantee",
    }
    save_json(folder / "manifest.json", manifest)
    return manifest


def verify(folder, config):
    manifest, original = load_snapshot(folder, config, strict=False)
    summary = inspect_pages(folder, manifest, config)
    if manifest["status"] == "complete":
        if summary["rows"] != manifest["expected_rows"] or summary != manifest["summary"]:
            raise PipelineError("Complete manifest does not match local data")
        after_path = folder / "discovery_after.json"
        if digest(after_path.read_bytes()) != manifest["discovery_after_sha256"]:
            raise PipelineError("Final discovery evidence checksum mismatch")
        if evidence_signature(read_json(after_path)) != evidence_signature(original):
            raise PipelineError("Source evidence differs across extraction")
        start, end = selected_window(config, manifest["mode"])
        expected_days = {row["day"][:10]: int(row["incidents"]) for row in original["days"]["rows"] if start[:10] <= row["day"][:10] < end[:10]}
        if summary["daily_counts"] != expected_days:
            raise PipelineError("Local daily counts differ from source evidence")
    return {"snapshot_id": folder.name, "status": manifest["status"], "verified_local_rows": summary["rows"], "ordered_ids_sha256": summary["ordered_ids_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["discover", "extract", "verify", "phase3", "phase4", "phase5", "phase6"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--snapshot", help="Existing snapshot ID to resume or verify")
    parser.add_argument("--mode", choices=["pilot", "full"], help="New snapshot scope (default: pilot); inferred on resume")
    parser.add_argument("--max-pages", type=int, help="Pause after this many new pages (resume check)")
    args = parser.parse_args()
    if args.max_pages is not None and (args.max_pages < 1 or args.command != "extract"):
        parser.error("--max-pages must be positive and is only valid for extract")
    if args.command in {"verify", "phase3", "phase4", "phase5", "phase6"} and not args.snapshot:
        parser.error(f"{args.command} requires --snapshot")
    if args.command == "discover" and args.snapshot:
        parser.error("discover always creates a new snapshot")
    tracemalloc.start()
    try:
        if args.command in {"verify", "phase3", "phase4", "phase5", "phase6"}:
            # Offline verification uses frozen inputs even after the workspace evolves.
            locator = read_json(args.config.resolve())
            folder = get_snapshot(locator, args.snapshot)
            config = read_json(folder / "config.json")
        else:
            config = load_config(args.config.resolve())
        if args.command == "verify":
            print(json.dumps(verify(folder, config), indent=2))
            return 0
        if args.command == "phase3":
            print(json.dumps(phase3(folder, config), indent=2))
            return 0
        if args.command == "phase4":
            print(json.dumps(phase4(folder, config), indent=2))
            return 0
        if args.command == "phase5":
            print(json.dumps(phase5(folder, config), indent=2))
            return 0
        if args.command == "phase6":
            print(json.dumps(phase6(folder, config), indent=2))
            return 0
        client = SocrataClient(config)
        if args.snapshot:
            folder = get_snapshot(config, args.snapshot)
            if args.mode and args.mode != read_json(folder / "manifest.json")["mode"]:
                raise PipelineError("Requested mode differs from the existing snapshot")
        else:
            mode = args.mode or "pilot"
            evidence = discover(client, config, mode)
            folder = create_snapshot(config)
            save_discovery(folder, config, evidence, mode)
        print(f"Snapshot: {folder.name}\nLocal directory: {folder}", flush=True)
        if args.command == "discover":
            print(f"Expected rows: {read_json(folder / 'manifest.json')['expected_rows']}", flush=True)
        else:
            manifest = extract(client, config, folder, args.max_pages)
            print(f"Status: {manifest['status']}; local rows: {manifest['summary']['rows']}", flush=True)
        return 0
    except (PipelineError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; resume the printed snapshot to verify and reuse saved pages.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
