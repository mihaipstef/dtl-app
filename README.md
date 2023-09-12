# dtl-app
Contains tools for running gnuradio applications in DTL environment

## App config example

A list of experiments in JSON format. Each experiment contains:
- top level config i.e. experiment name, monitoring config etc;
- ofdm_config: OFDM adaptive configuration;
- traffic generator: the tool used to generate traffic;
- live config: a set of parameters that can be changed on the fly, during run.
```
[
    {
        "name": "with_fec",
        "monitor_db": "mongodb://probe:probe@127.0.0.1:27017/probe_data?authSource=admin",
        "monitor_probe": "tcp://127.0.0.1:5555",
        "data_bytes": 100000,
        "skip": false,
        "traffic_generator": {
            "func": "icmp_ping",
            "kwargs": {
                "ping_rate": 1,
                "size": 64,
                "ip_addr": "3.3.3.3"
            }
        },
        "ofdm_config": {
            "sample_rate": 900000,
            "mcs": [[-100000, ["bpsk", "fec_1"]],
                    [11, ["qpsk", "fec_1"]],
                    [12, ["psk8", "fec_1"]],
                    [14, ["qam16", "fec_1"]]],
            "initial_mcs_id": 3,
            "fec_codes": [["fec_1", "n_0300_k_0152_gap_03.alist"]]
        },
        "live_config": {
            "direct_channel_noise_level": 0.8
        }
    }
]
```

## Setup tun interfaces

Setup 2 tun interafces and the routing rules required by `ofdm_adaptive_sim_tun` sim_cls by executing `setup_tun_env.sh` (see [Inject traffic in OFDM simulation via tun interafces](docs/local_tuntap_test_env.md)):
```
sudo ./setup_tun_env.sh
```

## Run experiment

Start experiments by calling `experiment.py` script:
```
sudo ./dtl-experiment/experiment.py --config experiments/experiment_fec.json --logs logs/ --sim_cls ofdm_adaptive_sim_tun
```
