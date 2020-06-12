# Prometheus Catalog

Simple service that keeps list of prometheus scrape targets in redis. The service allows servers to self-register for monitoring and prometheus to query the list of self-registered scrape targets.

Service can be used as sidecar container or standalone service.

`$FILE_SD_CONFIG` file can be used to directly integrate into Prometheus' scrape config, either by mounting the file to Prometheus container or as a sidecar container.

As a standalone service, cronjob can be used to periodically fetch with `http://<prometheus-catalog-host>/list` API call, format of the content matches `$FILE_SD_CONFIG` file.


## Usage

    docker run -p 5000:80 -v $(pwd)/state:/var/prometheus-catalog -ti --rm eficode/prometheus-catalog:latest


## Environment variables

- `DB_FILE`: Json database file name, use volume for persistence. Default: `/var/prometheus-catalog/db.json`
- `TIME_TO_LIVE`: Registered entry expiration time in seconds. Default is 1 day
- `FILE_SD_CONFIG`: Prometheus file-based service discovery, file can be used as is, therefore it can be mounted directly to Prometheus container. File is rewritten on every API change. Default: `/var/prometheus-catalog/file_sd_config.json`


## API

### Register

Example for registering:

    curl -d'{"labels":{"job":"nodes"},"targets":["node.some-domain.com:9100"],"hostname":"some-domain.com"}' -H'Content-Type: application/json' http://127.0.0.1:5000/register

If the metrics route is not "/metrics", but something else:

    curl -d'{"labels":{"job":"nodes","__metrics_path__":"/some-metrics"},"targets":["node.some-domain.com:9100"],"hostname":"some-domain.com"}' -H'Content-Type: application/json' http://127.0.0.1:5000/register

The subsequent registrations with same `hostname`, will update/add `labels` and/or add `targets`.
For removing `labels` or `targets`, you need to unregister first and then do the register again with correct values.
API will return Bad Request if the entry with same `labels` and `targets` already exist, regardless of `hostname` value.

### Unregister

    curl -XDELETE http://127.0.0.1:5000/unregister/some-domain.com

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


## Links

[Prometheus file-based service discovery file](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config)
