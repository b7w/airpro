AirPro
======

[![status-badge](https://woodpecker.b7w.me/api/badges/7/status.svg)](https://woodpecker.b7w.me/repos/7)

Simple analytic tool for AirVisual Pro

```mermaid
graph TD
    App[AirPro] --> |Read periodic via SMB| Sensor[AirVisual Pro]
    App[AirPro] --> |Save to| DB[ClickHouse]
    Grafana --> DB[ClickHouse]
```

Deploying
---------

```yaml
version: '3'
services:
    airpro:
        image: 'airpro:latest'
        restart: always
        ports:
            - 5000:5000
        environment:
            - CLICKHOUSE_URL=clickhouse://airpro:airpro@clickhouse:9000/airpro
            - DEVICE_HOST=172.17.1.101
            - DEVICE_PASSWORD=q1w2e3r4
            - TIMEZONE=Europe/Moscow
        logging:
            driver: json-file
            options:
                max-file: '2'
                max-size: '1m'

    clickhouse:
        image: 'yandex/clickhouse-server:20'
        restart: always
        ports:
            - 8123:8123
            - 9000:9000
        environment:
            - CLICKHOUSE_USER=airpro
            - CLICKHOUSE_PASSWORD=airpro
            - CLICKHOUSE_DB=airpro
        volumes:
            - './data/clickhouse:/var/lib/clickhouse'
        ulimits:
            nofile:
                soft: 262144
                hard: 262144
        logging:
            driver: json-file
            options:
                max-file: '2'
                max-size: '1m'

    grafana:
        image: 'grafana/grafana:7.3.6'
        restart: always
        ports:
            - 3000:3000
        environment:
            GF_INSTALL_PLUGINS: 'vertamedia-clickhouse-datasource'
        volumes:
            # Example config files in .etc
            - './grafana-main.ini:/etc/grafana/grafana.ini'
            - './grafana-datasources.yml:/etc/grafana/provisioning/datasources/provider.yml'
            - './grafana-dashboards.yml:/etc/grafana/provisioning/dashboards/provider.yml'
            - './airpro-dashboard.json:/etc/grafana/dashboards/airpro-dashboard.json:rw'
            - './data/grafana:/var/lib/grafana:rw'
        logging:
            driver: json-file
            options:
                max-file: '2'
                max-size: '1m'
```

About
-----

AirPro is open source project, released by MIT license.

Look, feel, be happy :-)
