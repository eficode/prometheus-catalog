#!/usr/bin/env python

from datetime import datetime, timedelta
from flask import Flask
from flask import request
from tinydb import TinyDB, where

import json
import os

# Used for develop mode
try:
    import uwsgidecorators
except Exception:
    print('Could not import `uwsgidecorators`, entry expiration will not work')

db_file = os.getenv('DB_FILE', 'db.json')
file_sd_config = os.getenv('FILE_SD_CONFIG', 'file_sd_config.json')
time_to_live = int(os.getenv('TIME_TO_LIVE', 60 * 60 * 24))
app = Flask('prometheus-catalog')
db = TinyDB(db_file)


@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/healthz')
def healthz():
    return ('OK', 200)


@app.route('/register', methods=['POST'])
def register():
    content = request.get_json()
    hostname = content.get('hostname')
    targets = content.get('targets', [])
    labels = content.get('labels', {})

    if not isinstance(hostname, str):
        return '`hostname` is required', 400

    if not isinstance(targets, list):
        return '`targets` is not a list', 400

    if not isinstance(labels, dict):
        return '`labels` is not a dict', 400

    current = db.get(where('hostname') == hostname)
    old_targets = []
    old_labels = {}
    if current is not None:
        old_targets = current['targets'] or []
        old_labels = current['labels'] or {}
    value = {
        'hostname': hostname,
        'labels': {**old_labels, **labels},
        'targets': sorted(list(set(targets + old_targets))),
        'expiration': (datetime.utcnow() + timedelta(seconds=time_to_live)
                       ).isoformat()
    }
    duplicate = db.get((where('hostname') != hostname) &
                       (where('labels') == value['labels']) &
                       (where('targets') == value['targets']))
    if duplicate is not None:
        return ('Refusing to update, duplicate value found at hostname `{}`'
                .format(duplicate['hostname'])), 400

    db.upsert(value, where('hostname') == hostname)
    update_file_sd_config()
    return '', 201


@app.route('/unregister/<hostname>', methods=['DELETE'])
def unregister(hostname):
    db.remove(where('hostname') == hostname)
    update_file_sd_config()
    return '', 204


@app.route('/list', methods=['GET'])
def list_endpoints():
    return json.dumps(get_file_sd_config()), 200, {
            'Content-Type': 'application/json; charset=utf-8'}


@app.route('/metrics', methods=['GET'])
def get_metrics():
    metrics = '\n'.join([
        'prometheus_catalog_hosts {}'.format(len(db)),
        'prometheus_catalog_up 1\n'
    ])
    return metrics, 200, {'Content-Type': 'text/plain'}


# Let's wrap into try-except block so that we can run in develop mode
try:
    @uwsgidecorators.timer(30)
    def remove_expired(num):
        print('Running cleanup of expired entries ...')
        db.remove(where('expiration') < datetime.utcnow().isoformat())
        update_file_sd_config()
except Exception as e:
    print(e)


def update_file_sd_config():
    with open(file_sd_config, 'w') as f:
        f.write(json.dumps(get_file_sd_config()))


def get_file_sd_config():
    data = db.all()
    result = []
    for elem in data:
        record = {'labels': elem['labels'], 'targets': elem['targets']}
        result.append(record)
    return result


update_file_sd_config()

# Run in develop mode
if __name__ == '__main__':
    app.run()
