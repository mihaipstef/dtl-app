from apps import (
    sim,
)
from gnuradio import (
    testbed,
)
import pytest
from testbed import (
    db,
    run,
)


@pytest.mark.parametrize("use_fec, expected_max_duration", [(True,2000), (False,1000)])
def test_fullduplex_ping(use_fec, expected_max_duration, tap_env):
    env_cfg = tap_env["env_cfg"]
    env_cfg["protocol"] = testbed.transported_protocol_t.MODIFIED_ETHER
    run_cfg = {
        "name": "latency_test",
        "data_bytes": 100000,
        "stop_condition": run.stop_condition.WHEN_TRAFFIC_DONE,
        "traffic": {
            "gen": {
                "name":"icmp_ping",
                "report": "IcmpPingReport",
                "params": {
                    "dst_ip_addr": "3.3.3.3",
                    "size": 10000,
                    "packets": 1
                }
            }
        },
        "app_config": {
            "sample_rate": 100000,
            "ofdm_config": {
                "sample_rate": 100000,
                "mcs": [[-100000, ["bpsk", "fec_1"]],
                        [13, ["qpsk", "fec_1"]],
                        [16, ["psk8", "fec_1"]],
                        [20, ["qam16", "fec_1"]]],
                "initial_mcs_id": 3
            },
            "live_config": {
                "direct_channel_noise_level": 0.1
            },
        }
    }
    if use_fec:
        run_cfg["app_config"]["ofdm_config"]["fec_codes"] = [["fec_1", "n_0300_k_0152_gap_03.alist"]]
    run.run_app(sim.ofdm_adaptive_full_duplex_sim, run_cfg, tap_env["name"], env_cfg)

    db_access = db.db("latency_test", overwrite=False, **env_cfg["monitor_db"])
    icmp_pings = db_access.query(func="count_documents", q={"ping_time": {"$exists": True}})
    assert(icmp_pings == 1)
    ping_report = db_access.query(func="find_one", q={"ping_time": {"$exists": True}})
    assert(ping_report["ping_time"] < expected_max_duration)