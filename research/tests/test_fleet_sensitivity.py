import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from research.experiments.fleet_sensitivity import (
    DEFAULT_CONFIG, atomic_json, file_hash, measured_utilization, scenarios, verify_completed, window_metrics,
)


class SensitivityTests(unittest.TestCase):
    def test_matrix_is_fixed_and_balanced(self):
        config = json.loads(DEFAULT_CONFIG.read_text(encoding='utf-8'))
        matrix = scenarios(config)
        self.assertEqual(len(matrix), 22)
        self.assertEqual(sum(s['family'] == 'fleet' for s in matrix), 12)
        self.assertEqual(len(matrix) * config['repetitions'] * len(config['policies']), 440)
        self.assertEqual({s['day'] for s in matrix if s['family'] == 'fleet'}, set(config['development_days']))

    def test_cohort_excludes_warmup_and_end_boundary_and_keeps_missing(self):
        def incident(minute, response, state):
            return {'tiempo_llamada': minute, 'tiempo_respuesta_min': response, 'estado': state,
                    'tiempo_despacho': None if state == 'pendiente' else minute + .5}
        engine = SimpleNamespace(incidents=[incident(9, 100, 'completado'), incident(10, 6, 'completado'),
                                            incident(19, None, 'pendiente'), incident(20, 30, 'completado')])
        metric = window_metrics(engine, 10, 20)
        self.assertEqual(metric['arrivals'], 2)
        self.assertEqual(metric['mean_response_min'], 6)
        self.assertEqual(metric['unanswered'], 1)
        self.assertEqual(metric['response_le_8min_pct_responded'], 100)
        self.assertEqual(metric['response_le_8min_pct_all_arrivals_lower_bound'], 50)
        self.assertIsNone(window_metrics(engine, 18, 20)['mean_response_min'])

    def test_utilization_clips_warmup_and_drain(self):
        engine = SimpleNamespace(busy_intervals=[(0, 12), (18, 25)], busy_since={1: 15},
                                 env=SimpleNamespace(now=30), fleet=[{}, {}])
        self.assertAlmostEqual(measured_utilization(engine, 10, 20), (2 + 2 + 5) / 20)

    def test_resume_detects_changed_results_and_incidents(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            artifact = directory / 'pair.parquet'
            artifact.write_bytes(b'test artifact')
            result = {'pair_id': 'pair', 'incidents_file': artifact.name, 'incidents_sha256': file_hash(artifact)}
            path = directory / 'pair.json'
            atomic_json(path, result)
            checksum = file_hash(path)
            self.assertEqual(verify_completed(directory, 'pair', checksum), result)
            artifact.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Incident artifact'):
                verify_completed(directory, 'pair', checksum)
            path.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Result missing or changed'):
                verify_completed(directory, 'pair', checksum)


if __name__ == '__main__':
    unittest.main()
