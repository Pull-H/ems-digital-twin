"""Tests for the prespecified temporal holdout design and daily inference."""

from __future__ import annotations

import unittest

import numpy as np

from research.experiments.july_holdout import (
    PROTOCOL_PATH,
    hac_mean,
    jobs_for_protocol,
    moving_block_interval,
    read_json,
)


class JulyHoldoutTests(unittest.TestCase):
    def test_protocol_jobs_use_independent_calendar_days(self):
        protocol = read_json(PROTOCOL_PATH)
        jobs = jobs_for_protocol(protocol)
        self.assertEqual(len(jobs), 210)
        self.assertEqual(len({scenario["day"] for scenario, _, _ in jobs}), 21)
        self.assertEqual(len({key for _, _, key in jobs}), 210)
        self.assertEqual({scenario["fleet"] for scenario, _, _ in jobs}, {400})
        self.assertEqual({scenario["demand_source"] for scenario, _, _ in jobs}, {"historical"})

    def test_block_bootstrap_is_reproducible_and_uses_days(self):
        days = np.arange(21, dtype=float)
        interval = moving_block_interval(days, 7, 10000, 20261023)
        self.assertEqual(interval, moving_block_interval(days, 7, 10000, 20261023))
        self.assertLess(interval[0], days.mean())
        self.assertGreater(interval[1], days.mean())
        with self.assertRaises(ValueError):
            moving_block_interval(days, 22, 10000, 20261023)

    def test_degenerate_daily_differences_are_explicit(self):
        zero = np.zeros(21)
        self.assertEqual(moving_block_interval(zero, 7, 10000, 20261023), (0.0, 0.0))
        self.assertEqual(hac_mean(zero), {"mean": 0.0, "ci95": [0.0, 0.0],
                                          "p_value": 1.0, "degenerate": True})


if __name__ == "__main__":
    unittest.main()
