# Prometheus Catalog

Simple service that keeps list of prometheus scrape targets in redis. The service allows servers to self-register for monitoring and prometheus to query the list of self-registered scrape targets.


## Usage

    docker run -p 5000:80 -v $(pwd)/db:/var/db -ti --rm eficode/prometheus-catalog:latest


## Environment variables

- `DB_FILE`: Json database file name, use volume for persistence. Default: `/var/db/db.json`
- `TIME_TO_LIVE`: Registered entry expiration time in seconds. Default is 1 day


## API

### Register

    curl -d'{"labels":{"foo":true,"bar":false},"targets":["127.0.0.1"],"hostname":"localhost"}' -H'Content-Type: application/json' http://127.0.0.1:5000/register

### Unregister

    curl -XDELETE http://127.0.0.1:5000/unregister/localhost

### List

    curl http://127.0.0.1:5000/list

### Metrics

    curl http://127.0.0.1:5000/metrics

### Health

    curl http://127.0.0.1:5000/healthz


## Develop

    virtualenv .
    pip install -r requirements.txt
    bin/python app/__init__.py

API will be available at port 5000, also note that entry expiration will not work when running without `uwsgi`
