# DTL testbed
Contains tools for running GNU Radio applications in real traffic conditions. The current implementation is tailored for DTL group needs and it only intends to demonstrate how to improve analysis and troubleshooting of radio communication protocols.

## Usage instructions

Because tesbed components depend on testbed library that is part of [DTL GNU Radio playground module](https://github.com/mihaipstef/gr-dtl) first the ```gr-dtl``` module has to be build and install.

```
> git clone https://github.com/mihaipstef/gr-dtl.git
> cd gr-dtl
> mkdir -p build && cd build
> cmake ..
> make -j4
> make install
> ldconfig
```

Once the ```gr-dtl``` module is installed the testbed can be used to manage testing environments using ```dtl_env``` script.

```
> git clone https://github.com/mihaipstef/dtl-testbed.git
> ./dtl-testbed/bin/dtl_env
usage: dtl_env [-h] {create,delete,run,start} ...

DTL environment management tool

positional arguments:
  {create,delete,run,start}
                        commands
    create              Create a DTL environment
    delete              Delete a DTL environment
    run                 Run an app in DTL environment
    start               Activate a DTL environment

options:
  -h, --help            show this help message and exit
```

## Testing an OFDM modem example

### Configuration

Part of DTL efforts is the implementation of a coded OFDM adaptive modem for which we developed the testbed.

**NOTE**
Some of the configuration parameters are application speciffic (i.e. ofdm_config and live_config).

|Section|Description|
|-|-|
|ofdm_config | OFDM adaptive configuration which is application speciffic|
|traffic_generator | Tool used to generate traffic|
|live_config| A set of parameters that the application is able to change on the fly. |

```json
[
    {
        "name": "ofdm_app_example",
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

## Run application in a DTL environment

See [Use DTL environments for GNU Radio applications](/docs/testing_environments.md)