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
                                        "training_window_end": '2026-04-01T01:00:00',
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

    def test_audit_is_observational_and_records_policy_choices(self):
        config = {**self.config, 'num_ambulances': 2, 'policy': 'predictivo'}
        plain = EMSSimulator(config)
        audited = EMSSimulator({**config, 'audit_decisions': True})
        self.assertEqual(plain.step(60), audited.step(60))
        self.assertEqual(len(plain.decision_audit), 0)
        first = audited.decision_audit[0]
        self.assertTrue(first['same_state_choice_changed'])
        self.assertEqual(first['selected_ambulance_id'], first['predictive_choice_id'])
        self.assertEqual(sum(c['available_count'] for c in first['candidates_by_zone']), 2)
        self.assertEqual(len(audited.decision_audit), 3)

    def test_duplicate_forecast_cannot_replace_missing_zone(self):
        self.forecasts.loc[self.forecasts.zone_id == 'QUEENS', 'zone_id'] = 'BRONX'
        with self.assertRaisesRegex(ValueError, 'duplicados'):
            EMSSimulator({**self.config, 'policy': 'predictivo'})

    def test_training_after_forecast_issue_is_rejected(self):
        self.forecasts['training_window_end'] = '2026-04-02'
        with self.assertRaisesRegex(ValueError, 'temporal'):
            EMSSimulator(self.config)

    def test_invalid_forecast_horizon_and_values_are_rejected(self):
        for column, value in (('prediction', float('nan')), ('prediction', -1),
                              ('target_end', self.epoch), ('training_window_end', None)):
            with self.subTest(column=column, value=value):
                original = self.forecasts[column].copy()
                self.forecasts[column] = value
                try:
                    with self.assertRaises(ValueError):
                        EMSSimulator(self.config)
                finally:
                    self.forecasts[column] = original

    def test_late_baseline_is_not_displayed_as_available(self):
        baseline = self.forecasts.copy()
        baseline['model_id'] = 'baseline_temporal_v1'
        baseline['issued_at'] += pd.Timedelta(hours=2)
        baseline['prediction'] = 999
        with patch('app.services.ems_simulator.data._forecasts', return_value=pd.concat([self.forecasts, baseline])):
            engine = EMSSimulator({**self.config, 'policy': 'predictivo'})
            self.assertTrue(all(p['demanda_predicha_base'] != 999 for p in engine.predictions(60)))

    def test_fractional_arrival_preserves_response_components(self):
        self.rows['sim_time_min'] = self.rows['sim_time_min'].astype(float)
        self.rows.loc[self.rows.incident_id == 'a', 'sim_time_min'] = 60.004
        engine = EMSSimulator(self.config)
        engine.step(60)
        incident = next(i for i in engine.incidents if i['id'] == 'a')
        self.assertEqual(incident['tiempo_llamada'], 60.004)
        self.assertAlmostEqual(incident['tiempo_respuesta_min'],
                               incident['tiempo_llegada_escena'] - 60.004)

    def test_conservation_and_unique_assignment_at_each_step(self):
        engine = EMSSimulator({**self.config, 'num_ambulances': 2})
        for _ in range(60):
            state = engine.step(1)
            assigned = [a['incidente_asignado_id'] for a in engine.fleet
                        if a['incidente_asignado_id'] is not None]
            self.assertEqual(len(assigned), len(set(assigned)))
            self.assertEqual(len(engine.fleet), 2)
            self.assertEqual(state['simulation']['completed'] + state['simulation']['unfinished'],
                             len(engine.incidents))
            self.assertGreaterEqual(state['metrics']['utilizacion_ambulancias'], 0)
            self.assertLessEqual(state['metrics']['utilizacion_ambulancias'], 1)

    def test_training_window_is_rejected(self):
        with self.assertRaises(ValueError):
            EMSSimulator({**self.config, 'start_minute': 0})

    def test_drain_finishes_queue_without_new_arrivals_or_future_forecasts(self):
        config = {**self.config, 'duration_min': 2, 'policy': 'predictivo'}
        engine = EMSSimulator(config)
        engine.step(2)
        before = len(engine.incidents)
        engine.forecasts = engine.forecasts[engine.forecasts.target_start < self.epoch + pd.Timedelta(hours=2)]
        final = engine.drain(120)
        self.assertEqual(len(engine.incidents), before)
        self.assertEqual(final['simulation']['completed'], 3)
        self.assertEqual(final['simulation']['unfinished'], 0)
        self.assertTrue(all(hour < engine.end for hour in engine.prediction_cache))
        self.assertGreater(engine.env.now, engine.end)

    def test_drain_cap_keeps_unresolved_cases_and_can_continue(self):
        engine = EMSSimulator({**self.config, 'duration_min': 2})
        with self.assertRaises(ValueError):
            engine.drain(5)
        engine.step(2)
        engine.drain(1)
        self.assertEqual(engine.env.now, 63)
        self.assertTrue(any(i['estado'] != 'completado' for i in engine.incidents))
        engine.drain(120)
        self.assertTrue(all(i['estado'] == 'completado' for i in engine.incidents))
        with self.assertRaises(ValueError):
            engine.drain(0)

    def test_sensitivity_only_scales_declared_components(self):
        base = EMSSimulator(self.config)
        scaled = EMSSimulator({**self.config, 'release_multiplier': 1.2, 'cross_zone_travel_multiplier': .8})
        base.step(1)
        scaled.step(1)
        self.assertEqual(base.incidents[0]['service'][:3], scaled.incidents[0]['service'][:3])
        self.assertAlmostEqual(scaled.incidents[0]['service'][3], base.incidents[0]['service'][3] * 1.2)
        unit = {**base.fleet[0], 'zona_actual_id': 2}
        incident = base.incidents[0]
        in_zone = incident['service'][0]
        self.assertAlmostEqual(scaled.travel(unit, incident) - in_zone, (base.travel(unit, incident) - in_zone) * .8)
        for value in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                EMSSimulator({**self.config, 'release_multiplier': value})

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
