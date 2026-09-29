import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from app.services.ems_simulator import EMSSimulator


class SimulatorTest(unittest.TestCase):
    def setUp(self):
        self.epoch = pd.Timestamp('2026-04-01')
        zones = [{"id": i, "nombre": name, "codigo": name, "centroide": [40.7, -74 + i * .001],
                  "poligono": [], "demanda_historica_diaria": 50} for i, name in [(1, 'BRONX'), (2, 'QUEENS')]]
        bases = [{"id": z['id'], "zona_id": z['id'], "latitud": z['centroide'][0], "longitud": z['centroide'][1]} for z in zones]
        self.scenario = {"zones": zones, "bases": bases, "hospitals": deepcopy(bases)}
        def row(identifier, minute, zone):
            return {"incident_id": identifier, "sim_time_min": minute, "zone_id": zone,
                    "incident_datetime_parsed": self.epoch + pd.Timedelta(minutes=minute),
                    "latitud": 40.7, "longitud": -74 + zone * .001, "prioridad": 'media', "tipo": 'otro',
                    "requiere_traslado": True, "response_cohort": True, "observed_response_min": 99,
                    "observed_assignment_to_scene_min": 2, "observed_scene_to_departure_min": 3,
                    "observed_transport_to_hospital_min": 1, "observed_call_to_close_min": 10}
        self.rows = pd.DataFrame([row('train1', 0, 1), row('train2', 1, 2), row('a', 60, 1), row('b', 60, 1), row('c', 61, 2)])
        self.forecasts = pd.DataFrame([{"model_id": 'hist_gradient_boosting_v1', "target_start": self.epoch + pd.Timedelta(hours=h),
                                        "issued_at": self.epoch + pd.Timedelta(hours=h), "target_end": self.epoch + pd.Timedelta(hours=h + 1),
                                        "zone_id": zone, "prediction": demand} for h in (1, 2) for zone, demand in [('BRONX', 30), ('QUEENS', 1)]])
        profile = {"window": {"start_inclusive": self.epoch.isoformat(), "end_exclusive": '2026-04-02T00:00:00'}}
        replacements = {'dataset_profile': profile, '_scenario': self.scenario, '_replay': self.rows,
                        '_forecasts': self.forecasts, '_snapshot_dir': Path('.'),
                        '_read_json': {'splits': {'train': {'end_exclusive': '2026-04-01T01:00:00'}}}}
        for name, result in replacements.items():
            patcher = patch(f'app.services.ems_simulator.data.{name}', return_value=result)
            patcher.start(); self.addCleanup(patcher.stop)
        self.config = {'start_minute': 60, 'duration_min': 60, 'num_ambulances': 1, 'seed': 42}
        self.runtime_dir = TemporaryDirectory()
        self.addCleanup(self.runtime_dir.cleanup)
        runtime_root = Path(self.runtime_dir.name)
        storage_patches = {
            'RUNTIME_DIR': runtime_root,
            'ACTIVE_PATH': runtime_root / 'active_simulation_run.json',
            'REGISTRY_PATH': runtime_root / 'simulation_runs_index.json',
            'RUNS_DIR': runtime_root / 'runs',
        }
        for name, value in storage_patches.items():
            patcher = patch(f'app.services.run_storage.{name}', value)
            patcher.start(); self.addCleanup(patcher.stop)

    def test_lifecycle_queue_release_and_no_future_response(self):
        engine = EMSSimulator(self.config)
        state = engine.step(1)
        self.assertEqual(state['metrics']['incidentes_totales'], 3)
        self.assertEqual(state['metrics']['incidentes_atendidos'], 0)
        self.assertEqual(state['metrics']['incidentes_pendientes'], 2)
        self.assertEqual(state['ambulances'][0]['estado'], 'en ruta')
        self.assertIsNone(state['simulation']['observed_response_mean'])
        final = engine.step(59)
        self.assertEqual(final['simulation']['completed'], 3)
        self.assertEqual(final['simulation']['unfinished'], 0)
        self.assertEqual(final['ambulances'][0]['estado'], 'disponible')
        self.assertGreater(final['metrics']['tiempo_promedio_respuesta'], 2)
        for incident in final['incidents']:
            self.assertLessEqual(incident['tiempo_llamada'], incident['tiempo_despacho'])
            self.assertLessEqual(incident['tiempo_despacho'], incident['tiempo_llegada_escena'])
            self.assertLessEqual(incident['tiempo_llegada_hospital'], incident['tiempo_liberacion'])

    def test_chunk_size_does_not_change_result(self):
        whole, chunked = EMSSimulator(self.config), EMSSimulator(self.config)
        for _ in range(12):
            chunked.step(5)
        self.assertEqual(whole.step(60), chunked.snapshot())

    def test_fleet_changes_queue(self):
        scarce = EMSSimulator(self.config).step(20)
        abundant = EMSSimulator({**self.config, 'num_ambulances': 3}).step(20)
        self.assertGreater(scarce['metrics']['tiempo_promedio_respuesta'], abundant['metrics']['tiempo_promedio_respuesta'])

    def test_policy_changes_dispatch_not_arrivals_or_service_samples(self):
        traditional = EMSSimulator({**self.config, 'num_ambulances': 2})
        predictive = EMSSimulator({**self.config, 'num_ambulances': 2, 'policy': 'predictivo'})
        traditional.step(1); predictive.step(1)
        self.assertEqual(traditional.arrivals, predictive.arrivals)
        self.assertEqual(traditional.incidents[0]['service'], predictive.incidents[0]['service'])
        self.assertNotEqual(traditional.incidents[0]['ambulancia_id'], predictive.incidents[0]['ambulancia_id'])

    def test_forecast_reproducibility_and_seed(self):
        config = {**self.config, 'demand_source': 'forecast'}
        a, b = EMSSimulator(config), EMSSimulator(config)
        self.assertEqual(a.arrivals, b.arrivals)
        self.assertNotEqual(a.arrivals, EMSSimulator({**config, 'seed': 43}).arrivals)
        self.assertTrue(all(r['incident_id'].startswith('SYN-') for r in a.arrivals))
        self.assertTrue(all(60 <= r['sim_time_min'] < 120 for r in a.arrivals))

    def test_missing_or_late_forecast_is_rejected(self):
        self.forecasts.loc[self.forecasts.zone_id == 'BRONX', 'issued_at'] += pd.Timedelta(hours=2)
        with self.assertRaises(ValueError):
            EMSSimulator({**self.config, 'demand_source': 'forecast'})

    def test_evaluation_outcomes_are_not_service_parameters(self):
        original = EMSSimulator(self.config).step(30)
        self.rows.loc[self.rows.sim_time_min >= 60, 'observed_assignment_to_scene_min'] = 999
        changed = EMSSimulator(self.config).step(30)
        self.assertEqual(original['metrics'], changed['metrics'])

    def test_training_window_is_rejected(self):
        with self.assertRaises(ValueError):
            EMSSimulator({**self.config, 'start_minute': 0})

    def test_observed_reference_requires_valid_response_cohort(self):
        self.rows.loc[self.rows.sim_time_min >= 60, 'response_cohort'] = False
        self.rows.loc[self.rows.sim_time_min >= 60, 'observed_response_min'] = 0
        state = EMSSimulator(self.config).step(60)
        self.assertEqual(state['simulation']['observed_response_count'], 0)
        self.assertIsNone(state['simulation']['observed_response_mean'])

    def test_api_validation_full_run_and_demo_guards(self):
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as client:
            config = {**self.config, 'data_mode': 'historical'}
            response = client.post('/api/simulations', json=config)
            self.assertEqual(response.status_code, 200, response.text)
            run_id = response.json()['run_id']
            self.assertEqual(client.get('/api/simulations').status_code, 200)
            self.assertEqual(client.get('/api/simulations/current').json()['run_id'], run_id)
            self.assertEqual(client.post('/api/simulations/restore/latest').json()['run_id'], run_id)
            for invalid in ({'num_ambulances': 0}, {'duration_min': -1}, {'demand_source': 'other'}, {'model_id': 'missing'}, {'start_minute': 0}):
                self.assertEqual(client.post('/api/simulations', json={**config, **invalid}).status_code, 422)
            self.assertEqual(client.post('/api/simulations/step', json={'delta_minutes': -1}).status_code, 422)
            self.assertEqual(client.get('/api/simulations/unknown').status_code, 404)
            self.assertEqual(client.patch('/api/simulations/config', json={'policy': 'predictivo'}).status_code, 409)
            self.assertNotEqual(client.get('/api/comparisons').status_code, 409)
            self.assertEqual(client.post('/api/predictions/train', json={}).status_code, 409)
            final = client.post(f'/api/simulations/{run_id}/run').json()['state']
            self.assertEqual(final['simulation']['completed'], 3)
            self.assertEqual(final['simulation']['status'], 'finished')
            self.assertEqual(client.get('/api/predictions').json(), final['predictions'])
            assistant = client.post('/api/assistant/query', json={'message': 'Interpreta la corrida actual'})
            self.assertEqual(assistant.status_code, 200)
            self.assertEqual(assistant.json()['intent'], 'simulacion')


if __name__ == '__main__':
    unittest.main()
