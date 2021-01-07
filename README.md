AirPro
======

[![Build Status](https://drone.b7w.me/api/badges/b7w/airpro/status.svg)](https://drone.b7w.me/b7w/airpro)

Simple analytic tool for AirVisual Pro

```mermaid
graph TD
    App[AirPro] --> |Read periodic via SMB| Sensor[AirVisual Pro]
    App[AirPro] --> |Save to| DB[ClickHouse]
    Grafana --> DB[ClickHouse]
```

About
-----

AirPro is open source project, released by MIT license.

Look, feel, be happy :-)
