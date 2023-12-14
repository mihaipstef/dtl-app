from apps import (
    sim,
)
import pytest
from testbed import (
    db,
    run,
)



@pytest.mark.parametrize("fixture_name, packets", [
    ("tun_env", 1),
    ("tap_env", 1)])
def test_fullduplex_ping(fixture_name, packets, request):
    run_cfg = {
        "name": "ofdm_fullduplex_test",
        "data_bytes": 100000,
        "stop_condition": run.stop_condition.WHEN_TRAFFIC_DONE,
        "traffic_generator": {
            "func": "icmp_ping",
            "kwargs": {
                "ping_rate": 1,
                "size": 64,
                "dst_ip_addr": "3.3.3.3",
                "packets": packets,
            }
        },
        "app_config": {
            "sample_rate": 100000,
            "ofdm_config": {
                "sample_rate": 100000,
                "mcs": [[-100000, ["bpsk", "fec_1"]],
                        [10, ["qpsk", "fec_1"]],
                        [13, ["psk8", "fec_1"]],
                        [20, ["qam16", "fec_1"]]],
                "initial_mcs_id": 1,
                "fec_codes": [["fec_1", "n_0300_k_0152_gap_03.alist"]]
            }
        },
        "live_config": {
            "direct_channel_noise_level": 0.65
        }
    }

    env = request.getfixturevalue(fixture_name)

    run.run_app(sim.ofdm_adaptive_full_duplex_sim, run_cfg, env["name"], env["env_cfg"])

    db_access = db.db("ofdm_fullduplex_test", overwrite=False, **env["env_cfg"]["monitor_db"])
    icmp_pings = db_access.query(func="count_documents", q={"ping_time": {"$exists": True}})

    assert(icmp_pings == packets)