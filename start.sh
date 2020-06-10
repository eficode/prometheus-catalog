#!/usr/bin/env bash
set -e
service nginx start

export DB_FILE="${DB_FILE:-/var/db/db.json}"
mkdir -p "$(dirname $DB_FILE)"
touch "$DB_FILE"
chown www-data:www-data "$DB_FILE"

uwsgi --ini uwsgi.ini
