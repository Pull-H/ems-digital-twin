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
    parser.add_argument("command", choices=["discover", "extract", "verify"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--snapshot", help="Existing snapshot ID to resume or verify")
    parser.add_argument("--mode", choices=["pilot", "full"], help="New snapshot scope (default: pilot); inferred on resume")
    parser.add_argument("--max-pages", type=int, help="Pause after this many new pages (resume check)")
    args = parser.parse_args()
    if args.max_pages is not None and (args.max_pages < 1 or args.command != "extract"):
        parser.error("--max-pages must be positive and is only valid for extract")
    if args.command == "verify" and not args.snapshot:
        parser.error("verify requires --snapshot")
    if args.command == "discover" and args.snapshot:
        parser.error("discover always creates a new snapshot")
    tracemalloc.start()
    try:
        if args.command == "verify":
            # Offline verification uses frozen inputs even after the workspace evolves.
            locator = read_json(args.config.resolve())
            folder = get_snapshot(locator, args.snapshot)
            config = read_json(folder / "config.json")
        else:
            config = load_config(args.config.resolve())
        if args.command == "verify":
            print(json.dumps(verify(folder, config), indent=2))
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
