#!/usr/bin/python

import re
import time
import argparse
from pprint import pprint
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
    # The build statuses we want to export about.
    resources = ["hosts", "", ]

    def __init__(self, target, user, password, insecure):
        self._target = target.rstrip("/")
        self._user = user
        self._password = password
        self._insecure = insecure
        self._prometheus_metrics = {}
        self._prefix = 'katello'
        
    def collect(self):
        start = time.time()

        self._setup_empty_prometheus_metrics()

        # Maybe not
        # number of hosts (total) -> index_hosts
        # number of facts (total) -> index_facts

        # puppet status: good, changed, bad, out-of-sync, disabled (total)
        # global health
        # subscriptions: hosts with susbcriptions, with invalid subscription
        # smart proxies health
        # tasks: running, stopped, planning, completed, failed

        for metric in self._prometheus_metrics:
            yield metric
        
        duration = time.time() - start
        COLLECTION_TIME.observe(duration)
        
    def _request_data(self, endpoint):
        url = '{0}{1}'.format(self._target, endpoint)
        if self._insecure:
            requests.packages.urllib3.disable_warnings()

        response = requests.get(
            url,
            params=None,
            data=None,
            auth=(self._user, self._password),
            verify=(not self._insecure))

        if DEBUG:
            pprint(response.text)

        if response.status_code != requests.codes.ok:
            raise Exception(
                "Call to url %s failed with status: %s" % (url, response.status_code))
        result = response.json()

        if DEBUG:
            pprint(result)

        return result

    def _setup_empty_prometheus_metrics(self):
        for host_status in [
                'active_hosts',
                'bad_hosts',
                'ok_hosts',
                'out_of_sync_hosts',
                'pending_hosts']:
            self._prometheus_metrics[host_status] = GaugeMetricFamily(
                '{0}_{1}'.format(self._prefix, host_status),
                '{0} number of {1}'.format(self._prefix, ' '.join(host_status.split('_'))),
                labels=['enabled'],
            )

    def _parse_katello_result(self, response):
        for metric in response:
            metric_name, metric_value, metric_labels = metric
            self._add_data_to_prometheus_structure(metric_name, metric_value, metric_labels)
            
    def _add_data_to_prometheus_structure(self, metric_name, value, labels):
        # Ignore metrics that have not been previously registered
        if metric_name in self._prometheus_metrics:
            if labels:
                self._prometheus_metrics[metric_name].labels(labels).set(value)
            else:
                self._prometheus_metrics[metric_name].set(value)

    # def _add_data_to_prometheus_structure(self, resource_name, data):
    #     self.prometheus_metrics[resource_name] = []

    #     for metric in data:
    #         metric_name = metric[0]
    #         metric_value = metric[1]
    #         metric_labels = metric[2]
    #         self._prometheus_metrics[resource_name].append(
    #              GaugeMetricFamily(
    #                  '{0}_{1}_{2}'.format(self._prefix, resource_name, metric_name),
    #                  '{0} number of {1}'.format(self._prefix, ' '.join(metric_name.split('_'))),
    #                  labels=metric_labels).set(metric_value))


def parse_args():
    parser = argparse.ArgumentParser(
        description='Katello exporter args jenkins address and port'
    )
    parser.add_argument(
        '-j', '--katello',
        metavar='katello',
        required=False,
        help='server url from the jenkins api',
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
        default=False
    )    
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(KatelloCollector(args.katello, args.user, args.password))
        start_http_server(port)
        print("Polling {}. Serving at port: {}".format(args.katello, port))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" Interrupted")
        exit(0)


if __name__ == "__main__":
    main()
