#!/usr/bin/env python

from datetime import datetime, timedelta
from flask import Flask
from flask import request
from pathlib import Path
from tinydb import TinyDB, where

import contextlib
import json
import os
import time

# Used for develop mode
try:
    import uwsgidecorators
except Exception:
    print('Could not import `uwsgidecorators`, entry expiration will not work')

db_file = os.getenv('DB_FILE', 'db.json')
file_sd_config = os.getenv('FILE_SD_CONFIG', 'file_sd_config.json')
time_to_live = int(os.getenv('TIME_TO_LIVE', 60 * 60 * 24))
app = Flask('prometheus-catalog')


@contextlib.contextmanager
def open_database(db_file, lock=False):
    '''
    Implements locking mechanism
        Is required for writing to file database since each process
        (because of uwsgi) keeps own instance of database.
    '''

    lock_file = '{}.lock'.format(db_file)

    def _acquire_lock():
        try:
            filename = Path(lock_file)
            filename.touch(exist_ok=False)  # must fail if lock exist
            return True
        except FileExistsError:
            return False

    def _remove_lock():
        filename = Path(lock_file)
        filename.unlink(missing_ok=True)  # missing_ok needs >= Python 3.8

    def _wait_and_lock():
        while not _acquire_lock():
            print('Database is locked, waiting ...')
            time.sleep(0.1)

    db = None
    try:
        if lock:
            _wait_and_lock()
        db = TinyDB(db_file)
        yield db
    finally:
        if db is not None:
            db.close()
        if lock:
            _remove_lock()


@app.route('/')
def hello():
    return 'Hello World!'


@app.route('/healthz')
def healthz():
    return ('OK', 200)


@app.route('/register', methods=['POST'])
def register():
    with open_database(db_file, lock=True) as db:
        content = request.get_json(force=True)
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
    with open_database(db_file, lock=True) as db:
        db.remove(where('hostname') == hostname)
        update_file_sd_config()
        return '', 204


@app.route('/list', methods=['GET'])
def list_endpoints():
    return json.dumps(get_file_sd_config()), 200, {
            'Content-Type': 'application/json; charset=utf-8'}


@app.route('/metrics', methods=['GET'])
def get_metrics():
    with open_database(db_file) as db:
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

        with open_database(db_file, lock=True) as db:
            db.remove(where('expiration') < datetime.utcnow().isoformat())
            update_file_sd_config()
except Exception as e:
    print(e)


def update_file_sd_config():
    with open(file_sd_config, 'w') as f:
        f.write(json.dumps(get_file_sd_config()))


def get_file_sd_config():
    with open_database(db_file) as db:
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
