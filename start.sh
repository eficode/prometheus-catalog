#!/usr/bin/env bash
set -e
service nginx start

export DB_FILE="${DB_FILE:-/srv/flask_app/db.json}"
touch "$DB_FILE"
chown www-data:www-data "$DB_FILE"

uwsgi --ini uwsgi.ini
