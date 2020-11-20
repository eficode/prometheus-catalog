#!/usr/bin/env bash
set -e
service nginx start

export DB_FILE="${DB_FILE:-/var/prometheus-catalog/db.json}"
export FILE_SD_CONFIG="${FILE_SD_CONFIG:-/var/prometheus-catalog/file_sd_config.json}"
mkdir -p "$(dirname $DB_FILE)"
chown -R www-data:www-data "$(dirname $DB_FILE)"
touch "$DB_FILE"
chown www-data:www-data "$DB_FILE"
rm -f "${DB_FILE}.lock"  # since start.sh is ran on start of all processes we can delete lock file
touch "$FILE_SD_CONFIG"
chown www-data:www-data "$FILE_SD_CONFIG"

uwsgi --ini uwsgi.ini
