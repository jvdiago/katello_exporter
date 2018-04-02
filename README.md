# Katello Exporter

[![Build Status](https://api.travis-ci.org/jvdiago/katello_exporter.svg?branch=master)](https://travis-ci.org/jvdiago/katello_exporter)

Katello exporter for prometheus.io, written in python.

This exporter is based on https://github.com/lovoo/jenkins_exporter

## Usage

    katello_exporter.py [-h] [-j katello] [--user user] [-k]
                        [--password password] [-p port]

    optional arguments:
      -h, --help            show this help message and exit
      -j katelllo, --katello katello
                            server url from the katello api
      --user user           katello api user
      --password password   katello api password
      -p port, --port port  Listen to this port
      -k, --insecure        Allow connection to insecure katello API

#### Example

    docker run -d -p 9118:9118 jvela/katello_exporter:latest -j https://katello:443 -p 9118


## Installation

    git clone git@github.com:jvdiago/katello_exporter.git
    cd katelo_exporter
    pip install -r requirements.txt

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request
