#!/usr/bin/env python

import time
import argparse
from pprint import pprint
import json
import requests
import os
from sys import exit
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY

DEBUG = int(os.environ.get('DEBUG', '0'))

COLLECTION_TIME = Summary(
    'katello_collector_collect_seconds',
    'Time spent to collect metrics from Katello')


class KatelloCollector(object):
    def __init__(self, target, user, password, insecure):
        self._target = target.rstrip("/")
        self._user = user
        self._password = password
        self._insecure = insecure
        self._prometheus_metrics = {}

        # Endpoints
        dashboard_endpoints = [('dashboard', '/api/dashboard')]
        task_endpoints = [('tasks', '/foreman_tasks/api/tasks/summary')]
        subscription_endpoints = [
            ('partial', '/api/v2/hosts?search=+subscription_status+%3D+partial'),
            ('valid', '/api/v2/hosts?search=+subscription_status+%3D+valid'),
            ('invalid', '/api/v2/hosts?search=+subscription_status+%3D+invalid'),
            ('unknown', '/api/v2/hosts?search=+subscription_status+%3D+unknown'),

        ]
        service_endpoints = [('services', '/katello/api/ping')]

        self._endpoints = [
            (dashboard_endpoints, self._store_dashboard_data),
            (task_endpoints, self._store_task_data),
            (subscription_endpoints, self._store_subscription_data),
            (service_endpoints, self._store_service_data)
        ]

        # Metric Names
        self._dashboard_complex_metrics = [
            'katello_active_hosts_ok',
            'katello_bad_hosts',
            'katello_ok_hosts',
            'katello_out_of_sync_hosts',
            'katello_good_hosts',
            'katello_pending_hosts'
        ]
        self._dashboard_simple_metrics = [
            'katello_active_hosts',
            'katello_reports_missing',
            'katello_total_hosts']
        self._task_metrics = 'katello_tasks_status'
        self._subscription_metrics = 'katello_subscription_status'
        self._service_metrics = 'katello_service_status'

    def collect(self):
        start = time.time()

        self._setup_empty_prometheus_metrics()

        for metrics in self._endpoints:
            endpoints, store_func = metrics
            try:
                store_func(self._get_endpoints_data(endpoints))
            except requests.exceptions.ConnectionError as e:
                print('Error connecting to server {0}. {1}'.format(self._target, e))
            except Exception as e:
                print('Unknown error retreving data in endpoints {0}. {1}'.format(endpoints, e))

        for metric in self._prometheus_metrics.values():
            yield metric

        duration = time.time() - start
        COLLECTION_TIME.observe(duration)

    def _request_data(self, endpoint, data=None, params=None):
        url = '{0}{1}'.format(self._target, endpoint)
        if self._insecure:
            requests.packages.urllib3.disable_warnings()

        if data:
            data = json.dumps(data)

        response = requests.get(
            url,
            params=params,
            data=data,
            auth=(self._user, self._password),
            verify=(not self._insecure))

        if DEBUG:
            pprint(response.text)

        if response.status_code != requests.codes.ok:
            raise Exception(
                "Call to url %s failed with status: %s" % (url, response.status_code))
        try:
            result = response.json()
        except json.decoder.JSONDecodeError:
            result = response

        if DEBUG:
            pprint(result)

        return result

    def _setup_empty_prometheus_metrics(self):
        for host_status in self._dashboard_complex_metrics:
            self._prometheus_metrics[host_status] = GaugeMetricFamily(
                host_status,
                'Number of {0}'.format(' '.join(host_status.split('_'))),
                labels=['enabled'],
            )

        for host_status in self._dashboard_simple_metrics:
            self._prometheus_metrics[host_status] = GaugeMetricFamily(
                host_status,
                'Number of {0}'.format(' '.join(host_status.split('_'))),
            )

        self._prometheus_metrics[self._service_metrics] = GaugeMetricFamily(
            self._service_metrics,
            'Service status',
            labels=['service_status', 'service']
        )

        self._prometheus_metrics[self._subscription_metrics] = GaugeMetricFamily(
            self._subscription_metrics,
            'Subscription status',
            labels=['subscription_status'],
        )

        self._prometheus_metrics[self._task_metrics] = GaugeMetricFamily(
            self._task_metrics,
            'Task status',
            labels=['task_status'],
        )

    def _get_endpoints_data(self, endpoints):
        data = {}
        for endpoint in endpoints:
            endpoint_name, endpoint_url = endpoint
            raw_data = self._request_data(endpoint_url)
            data[endpoint_name] = raw_data

        return data

    def _store_dashboard_data(self, data):
        for endpoint_name, endpoint_data in data.items():
            for puppet_status, count in endpoint_data.items():
                metric_name = 'katello_' + \
                    puppet_status.replace('_enabled', '')
                enabled = 'true' if 'enabled' in puppet_status else 'false'

                if metric_name in self._dashboard_complex_metrics:
                    self._add_data_to_prometheus_structure(
                        metric_name, count, [enabled])
                elif metric_name in self._dashboard_simple_metrics:
                    self._add_data_to_prometheus_structure(metric_name, count)

    def _store_task_data(self, data):
        available_statuses = ['paused', 'running', 'stopped', 'planned']
        sanitized_data = {}
        for endpoint_name, endpoint_data in data.items():
            for task_status in endpoint_data:
                status = task_status['state']
                count = task_status['count']
                # There are repeated statuses depending no the result. Adding all of them
                sanitized_data[status] = sanitized_data.get(status, 0) + count

        # Ensure we always return all the possible statuses
        for status in available_statuses:
            if status not in sanitized_data:
                sanitized_data[status] = 0

        for status, count in sanitized_data.items():
            self._add_data_to_prometheus_structure(
                self._task_metrics, count, [status])

    def _store_subscription_data(self, data):
        for endpoint_name, endpoint_data in data.items():
            count = len(endpoint_data['results'])
            status = endpoint_name
            self._add_data_to_prometheus_structure(
                self._subscription_metrics, count, [status])

    def _store_service_data(self, data):
        status_values = ['ok', 'fail']

        for endpoint_name, endpoint_data in data.items():
            services = endpoint_data['services']
            for service_name, service_data in services.items():
                service_status = service_data['status']
                for status in status_values:
                    value = 1 if service_status.lower() == status else 0
                    self._add_data_to_prometheus_structure(
                        self._service_metrics, value, [status, service_name])

    def _add_data_to_prometheus_structure(self, metric_name, value, labels=[]):
        # Ignore metrics that have not been previously registered
        if metric_name in self._prometheus_metrics:
            self._prometheus_metrics[metric_name].add_metric(labels, value)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Katello exporter args katello address and port'
    )
    parser.add_argument(
        '-j', '--katello',
        metavar='katello',
        required=False,
        help='server url from the katello api',
        default=os.environ.get('KATELLO_SERVER', 'https://katello')
    )
    parser.add_argument(
        '--user',
        metavar='user',
        required=False,
        help='Katello api user',
        default=os.environ.get('KATELLO_USER')
    )
    parser.add_argument(
        '--password',
        metavar='password',
        required=False,
        help='Katello api password',
        default=os.environ.get('KATELLO_PASSWORD')
    )
    parser.add_argument(
        '-p', '--port',
        metavar='port',
        required=False,
        type=int,
        help='Listen to this port',
        default=int(os.environ.get('VIRTUAL_PORT', '443'))
    )
    parser.add_argument(
        '-k', '--insecure',
        dest='insecure',
        required=False,
        action='store_true',
        help='Allow connection to insecure Katello API',
        default=bool(os.environ.get('INSECURE', False))
    )
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(KatelloCollector(
            args.katello, args.user, args.password, args.insecure))
        start_http_server(port)
        print("Polling {}. Serving at port: {}".format(args.katello, port))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
