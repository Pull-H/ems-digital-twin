import copy
from collections import Counter
from datetime import datetime, timedelta
import gzip
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from research.pipeline import nyc_ems as pipeline


class FakeClient:
    def __init__(self, config):
        self.config = config
        self.requests = 0
        self.response_bytes = 0
        self.offsets = []
        self.download_queries = []
        self.marker = 1
        self.rows = [
            {"incident_id": f"ID-{day}", "incident_datetime": f"2026-04-0{day}T12:00:00.000", "borough": "MANHATTAN"}
            for day in range(1, 8)
        ]

    def metadata(self):
        import csv
        with pipeline.repository_path(self.config["source"]["field_contract_path"]).open() as handle:
            fields = list(csv.DictReader(handle))
        types = {"string": "text", "local_datetime": "calendar_date", "number": "number"}
        return {"rowsUpdatedAt": self.marker, "columns": [
            {"fieldName": field["field"], "dataTypeName": types[field["normalized_type"]]} for field in fields
        ]}

    def query(self, params):
        self.requests += 1
        select = params["$select"]
        selected = self.rows
        if "$where" in params:
            start, end = re.findall(r"'([^']+)'", params["$where"])
            selected = [row for row in self.rows if start <= row["incident_datetime"] < end]
        if "$offset" in params:
            offset = params["$offset"]
            self.offsets.append(offset)
            self.download_queries.append(params.copy())
            rows = selected[offset:offset + params["$limit"]]
        elif "unique_ids" in select:
            rows = [{"incidents": str(len(selected)), "unique_ids": str(len({row['incident_id'] for row in selected}))}]
        elif "date_trunc_ymd" in select:
            counts = Counter(row["incident_datetime"][:10] for row in selected)
            rows = [{"day": day + "T00:00:00.000", "incidents": str(count)} for day, count in sorted(counts.items())]
        elif "date_trunc_ym" in select:
            counts = Counter(row["incident_datetime"][:7] for row in selected)
            rows = [{"month": month + "-01T00:00:00.000", "incidents": str(count)} for month, count in sorted(counts.items())]
        else:
            rows = [{"earliest": self.rows[0]["incident_datetime"], "latest": self.rows[-1]["incident_datetime"]}]
        raw = json.dumps(rows).encode()
        self.response_bytes += len(raw)
        return rows, raw, "https://example.test/?" + pipeline.urlencode(params)


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.config = pipeline.load_config(pipeline.DEFAULT_CONFIG)
        self.config["extraction"]["page_size"] = 3
        test_root = pipeline.ROOT / "research/artifacts/test-work"
        test_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=test_root)
        self.folder = Path(self.temporary.name)
        self.config["paths"]["models_root"] = (self.folder / "artifacts").relative_to(pipeline.ROOT).as_posix()
        self.client = FakeClient(self.config)
        self.evidence = pipeline.discover(self.client, self.config)
        pipeline.save_discovery(self.folder, self.config, self.evidence)

    def tearDown(self):
        self.assertTrue(self.folder.resolve().is_relative_to(pipeline.ROOT / "research/artifacts/test-work"))
        self.temporary.cleanup()

    def test_resume_and_completed_rerun_reuse_pages(self):
        paused = pipeline.extract(self.client, self.config, self.folder, max_pages=1)
        self.assertEqual(paused["status"], "paused")
        first_hash = paused["pages"][0]["sha256"]
        completed = pipeline.extract(self.client, self.config, self.folder)
        self.assertEqual(self.client.offsets, [0, 3, 6])
        self.assertEqual(completed["summary"]["rows"], 7)
        self.assertEqual(completed["summary"]["unique_ids"], 7)
        self.assertEqual(completed["pages"][0]["sha256"], first_hash)
        self.assertEqual(completed["summary"]["missing_values"]["zipcode"], 7)
        self.assertEqual(pipeline.verify(self.folder, self.config)["status"], "complete")
        same = pipeline.extract(self.client, self.config, self.folder)
        self.assertEqual(same["sessions"][-1]["pages_downloaded"], 0)
        self.assertEqual(self.client.offsets, [0, 3, 6])
        self.assertEqual(same["summary"]["ordered_ids_sha256"], completed["summary"]["ordered_ids_sha256"])

    def test_phase3_writes_quality_and_cohort_artifacts(self):
        pipeline.extract(self.client, self.config, self.folder)
        result = pipeline.phase3(self.folder, self.config)
        self.assertEqual(result["source_rows"], 7)
        self.assertEqual(result["demand_cohort_rows"], 7)
        self.assertTrue((self.folder / "interim/quality_report.json").exists())
        self.assertTrue((self.folder / "interim/quarantine.csv").exists())
        self.assertTrue((self.folder / "processed/incidents_clean.parquet").exists())
        self.assertTrue((self.folder / "processed/demand_cohort.parquet").exists())
        summary = pipeline.read_json(self.folder / "processed/cohort_summary.json")
        self.assertEqual(summary["source_rows"], 7)
        self.assertEqual(summary["excluded_from_demand"]["duplicate_incident_id"], 0)

    def test_phase4_writes_hourly_panel_and_simulation_events(self):
        pipeline.extract(self.client, self.config, self.folder)
        pipeline.phase3(self.folder, self.config)
        result = pipeline.phase4(self.folder, self.config)
        self.assertGreater(result["panel_rows"], 0)
        self.assertEqual(result["simulation_events"], 7)
        self.assertTrue((self.folder / "processed/hourly_demand_panel.parquet").exists())
        self.assertTrue((self.folder / "processed/model_ready_hourly_demand_panel.parquet").exists())
        self.assertTrue((self.folder / "processed/feature_dictionary.json").exists())
        self.assertTrue((self.folder / "processed/temporal_partitions.json").exists())
        self.assertTrue((self.folder / "processed/geography_summary.json").exists())
        self.assertTrue((self.folder / "simulation/historical_incident_events.parquet").exists())

    def test_phase5_trains_three_models_and_writes_reports(self):
        pipeline.extract(self.client, self.config, self.folder)
        pipeline.phase3(self.folder, self.config)
        pipeline.phase4(self.folder, self.config)
        result = pipeline.phase5(self.folder, self.config)
        self.assertEqual(result["models_compared"], 3)
        self.assertIn(result["best_model_id"], {
            "baseline_temporal_v1",
            "random_forest_v1",
            "hist_gradient_boosting_v1",
        })
        self.assertTrue((self.folder / "processed/retrospective_forecasts.parquet").exists())
        metrics = pipeline.repository_path(result["metrics"])
        model_card = pipeline.repository_path(result["model_card"])
        predictions = pipeline.repository_path(result["predictions"])
        self.assertTrue(metrics.exists())
        self.assertTrue(model_card.exists())
        self.assertTrue(predictions.exists())

    def test_phase6_writes_historical_replay_and_calibration_package(self):
        pipeline.extract(self.client, self.config, self.folder)
        pipeline.phase3(self.folder, self.config)
        pipeline.phase4(self.folder, self.config)
        pipeline.phase5(self.folder, self.config)
        result = pipeline.phase6(self.folder, self.config)
        self.assertEqual(result["historical_arrivals"], 7)
        self.assertTrue((self.folder / "simulation/historical_replay_inputs.parquet").exists())
        self.assertTrue((self.folder / "simulation/observed_time_components.parquet").exists())
        self.assertTrue((self.folder / "simulation/calibration_parameters.json").exists())
        self.assertTrue((self.folder / "simulation/nyc_scenario.json").exists())
        self.assertTrue((self.folder / "simulation/resource_assumptions.json").exists())
        self.assertTrue((self.folder / "simulation/phase6_manifest.json").exists())

    def test_tampered_page_is_rejected_before_new_download(self):
        manifest = pipeline.extract(self.client, self.config, self.folder, max_pages=1)
        (self.folder / manifest["pages"][0]["path"]).write_bytes(b"corrupt")
        with self.assertRaisesRegex(pipeline.PipelineError, "checksum"):
            pipeline.extract(self.client, self.config, self.folder)
        self.assertEqual(self.client.offsets, [0])

    def test_changed_source_invalidates_snapshot(self):
        pipeline.extract(self.client, self.config, self.folder, max_pages=1)
        self.client.marker = 2
        with self.assertRaisesRegex(pipeline.PipelineError, "Source changed"):
            pipeline.extract(self.client, self.config, self.folder)
        self.assertEqual(pipeline.read_json(self.folder / "manifest.json")["status"], "invalidated")
        self.assertEqual(self.client.offsets, [0])

    def test_source_schema_type_change_rejected(self):
        metadata = self.client.metadata()
        metadata["columns"][0]["dataTypeName"] = "number"
        with self.assertRaisesRegex(pipeline.PipelineError, "schema mismatch"):
            pipeline.schema_guard(metadata, self.config)

    def test_source_duplicate_ids_rejected(self):
        self.client.rows[1]["incident_id"] = self.client.rows[0]["incident_id"]
        with self.assertRaisesRegex(pipeline.PipelineError, "not unique"):
            pipeline.discover(self.client, self.config)

    def test_out_of_window_row_rejected_even_with_correct_checksums(self):
        manifest = pipeline.extract(self.client, self.config, self.folder, max_pages=1)
        page = manifest["pages"][0]
        rows = copy.deepcopy(self.client.rows[:3])
        rows[0]["incident_datetime"] = "2026-03-31T12:00:00.000"
        raw = json.dumps(rows).encode()
        compressed = gzip.compress(raw, mtime=0)
        (self.folder / page["path"]).write_bytes(compressed)
        page.update(sha256=pipeline.digest(compressed), raw_sha256=pipeline.digest(raw), raw_bytes=len(raw), compressed_bytes=len(compressed))
        with self.assertRaisesRegex(pipeline.PipelineError, "outside pilot"):
            pipeline.inspect_pages(self.folder, manifest, self.config)

    def test_config_change_blocks_resume(self):
        changed = copy.deepcopy(self.config)
        changed["extraction"]["page_size"] = 2
        with self.assertRaisesRegex(pipeline.PipelineError, "changed"):
            pipeline.load_snapshot(self.folder, changed)

    def test_http_429_respects_retry_after(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"[]"

        error = HTTPError("https://example.test", 429, "rate limited", {"Retry-After": "7"}, None)
        with patch.object(pipeline, "urlopen", side_effect=[error, Response()]), patch.object(pipeline.time, "sleep") as sleep:
            client = pipeline.SocrataClient(self.config)
            self.assertEqual(client.query({"$limit": 1})[0], [])
            sleep.assert_called_once_with(7.0)
            self.assertEqual(client.requests, 2)

    def test_http_400_not_retried(self):
        error = HTTPError("https://example.test", 400, "bad query", {}, None)
        with patch.object(pipeline, "urlopen", side_effect=error) as request, patch.object(pipeline.time, "sleep") as sleep:
            with self.assertRaisesRegex(pipeline.PipelineError, "HTTP 400"):
                pipeline.SocrataClient(self.config).query({"$limit": 1})
            self.assertEqual(request.call_count, 1)
            sleep.assert_not_called()

    def prepare_full(self):
        self.config["extraction"]["page_size"] = 20
        start = datetime(2026, 4, 1, 12)
        self.client.rows = [
            {"incident_id": f"DAY-{i:03d}", "incident_datetime": (start + timedelta(days=i)).isoformat()}
            for i in range(91)
        ]
        evidence = pipeline.discover(self.client, self.config, "full")
        pipeline.save_discovery(self.folder, self.config, evidence, "full")

    def test_month_boundaries_resume_and_idempotency(self):
        self.prepare_full()
        paused = pipeline.extract(self.client, self.config, self.folder, max_pages=2)
        self.assertEqual(paused["summary"]["rows"], 30)
        first_hashes = [page["sha256"] for page in paused["pages"]]
        result = pipeline.extract(self.client, self.config, self.folder)
        self.assertEqual(self.client.offsets, [0, 20, 0, 20, 0, 20])
        self.assertEqual([part["expected_rows"] for part in result["partitions"]], [30, 31, 30])
        self.assertEqual(result["summary"]["rows"], 91)
        self.assertEqual(first_hashes, [page["sha256"] for page in result["pages"][:2]])
        self.assertTrue(result["pages"][2]["path"].startswith("raw/2026-05/"))
        self.assertEqual(pipeline.verify(self.folder, self.config)["status"], "complete")
        again = pipeline.extract(self.client, self.config, self.folder)
        self.assertEqual(again["sessions"][-1]["pages_downloaded"], 0)

    def test_duplicate_id_between_months_blocks_discovery(self):
        self.prepare_full()
        self.client.rows[31]["incident_id"] = self.client.rows[0]["incident_id"]
        with self.assertRaisesRegex(pipeline.PipelineError, "Full-window IDs"):
            pipeline.discover(self.client, self.config, "full")

    def test_corrupt_archived_mapping_blocks_verification(self):
        (self.folder / "provenance/mappings.json").write_text("{}")
        with self.assertRaisesRegex(pipeline.PipelineError, "provenance checksum"):
            pipeline.verify(self.folder, self.config)

    def test_offline_verify_accepts_new_extractor_but_resume_rejects_it(self):
        pipeline.extract(self.client, self.config, self.folder)
        original = pipeline.lineage(self.config)
        with patch.object(pipeline, "lineage", return_value={**original, "extractor_sha256": "new-version"}):
            self.assertEqual(pipeline.verify(self.folder, self.config)["verified_local_rows"], 7)
            with self.assertRaisesRegex(pipeline.PipelineError, "changed"):
                pipeline.load_snapshot(self.folder, self.config)

    def test_wrong_partition_count_rejected(self):
        self.prepare_full()
        path = self.folder / "manifest.json"
        manifest = pipeline.read_json(path)
        manifest["partitions"][0]["expected_rows"] += 1
        pipeline.save_json(path, manifest)
        with self.assertRaisesRegex(pipeline.PipelineError, "Partition plan"):
            pipeline.verify(self.folder, self.config)


if __name__ == "__main__":
    unittest.main()
