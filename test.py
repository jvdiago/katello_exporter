#!/usr/bin/env python

import unittest
from katello_exporter import KatelloCollector


class KatelloCollectorTestCase(unittest.TestCase):
    # The build statuses we want to export about.
    # TODO: add more test cases

    def test_prometheus_metrics(self):
        exporter = KatelloCollector('', '', '', False)
        self.assertEqual(exporter._prometheus_metrics, {})

        exporter._setup_empty_prometheus_metrics()
        all_metrics = exporter._dashboard_complex_metrics + \
                      exporter._dashboard_simple_metrics + \
                      [exporter._task_metrics] + \
                      [exporter._subscription_metrics] + \
                      [exporter._service_metrics]
        self.assertEqual(sorted(exporter._prometheus_metrics.keys()), sorted(all_metrics))


if __name__ == "__main__":
    unittest.main()
