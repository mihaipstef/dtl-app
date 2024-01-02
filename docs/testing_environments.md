# Use DTL environments for GNU Radio applications

## Create environment

Environment configuration is performed via json config file

```json
{
    "monitor_db": {
        "db_type": "mongo",
        "access": {
            "uri": "mongodb://<user>:<password>@<db ip address>:27017/monitor?authSource=admin"
        },
    },
    "monitor_probe": "tcp://127.0.0.1:5555",
    "type": "sim",
    "mode": "tap",
    "tunnel": [["2.2.2.2"], ["3.3.3.3"]]
}
```
|Parameter|Description|
|---------|-----------|
| monitor_db | Settings of the database used to store the monitoring data. We keep experimenting with databases that are specialized in storig timeseries but we use MongoDB as default. |
| monitor_probe | URL of the ZeroMQ probe that aggregates and wires the monitoring data from the application |
| type | The environment type is ```sim``` for simulation (both network interfaces are in the same environment) or ```real``` for execution with SDR boards (use two independent environments to be able to run on separate machines).|
| mode | The type of the interfaces used to inject traffic in the application (ie ```tun```/```tap```).|
| tunnel | The IP and MAC (optional) addresses of the interfaces.|

Easily create a new environment:

```bash
sudo ./dtl-testbed/bin/dtl_env create test_tap --config=dtl-testbed/apps/config/sim_env.json
```


## Start the environment

```bash
sudo ./dtl-testbed/bin/dtl_env start test_tap
```

## Run application in environment

```bash
sudo ./dtl-testbed/bin/dtl_env run --name test_tap --config ./dtl-testbed/apps/config/app_cfg.json ofdm_adaptive_full_duplex_sim
```