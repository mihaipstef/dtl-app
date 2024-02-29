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



@pytest.mark.parametrize("fixture_name, packets, packet_sz, protocol, use_fec", [
    ("tun_env", 5, 100, testbed.transported_protocol_t.IPV4_ONLY, False),
    ("tap_env", 5, 100, testbed.transported_protocol_t.ETHER_IPV4, False),
    ("tap_env", 5, 100, testbed.transported_protocol_t.MODIFIED_ETHER, False),
    ("tun_env", 5, 100, testbed.transported_protocol_t.IPV4_ONLY, True),
    ("tap_env", 5, 100, testbed.transported_protocol_t.ETHER_IPV4, True),
    ("tap_env", 5, 100, testbed.transported_protocol_t.MODIFIED_ETHER, True),
    ("tun_env", 2, 10000, testbed.transported_protocol_t.IPV4_ONLY, False),
    ("tap_env", 2, 10000, testbed.transported_protocol_t.ETHER_IPV4, False),
    ("tap_env", 2, 10000, testbed.transported_protocol_t.MODIFIED_ETHER, False),
    ("tun_env", 2, 10000, testbed.transported_protocol_t.IPV4_ONLY, True),
    ("tap_env", 2, 10000, testbed.transported_protocol_t.ETHER_IPV4, True),
    ("tap_env", 2, 10000, testbed.transported_protocol_t.MODIFIED_ETHER, True),])
def test_fullduplex_ping(fixture_name, packets, packet_sz, protocol, use_fec, request):
    env = request.getfixturevalue(fixture_name)
    env_cfg = env["env_cfg"]
    env_cfg["protocol"] = protocol
    run_cfg = {
        "name": "ofdm_fullduplex_test",
        "data_bytes": 100000,
        "stop_condition": run.stop_condition.WHEN_TRAFFIC_DONE,
        "traffic_generator": {
            "func": "icmp_ping",
            "kwargs": {
                "ping_rate": 0.5,
                "size": packet_sz,
                "dst_ip_addr": "3.3.3.3",
                "packets": packets,
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
                "initial_mcs_id": 1
            },
            "live_config": {
                "direct_channel_noise_level": 0.5
            },
        }
    }
    if use_fec:
        run_cfg["app_config"]["ofdm_config"]["fec_codes"] = [["fec_1", "n_0300_k_0152_gap_03.alist"]]
    run.run_app(sim.ofdm_adaptive_full_duplex_sim, run_cfg, env["name"], env_cfg)

    db_access = db.db("ofdm_fullduplex_test", overwrite=False, **env_cfg["monitor_db"])
    icmp_pings = db_access.query(func="count_documents", q={"ping_time": {"$exists": True}})
    assert(icmp_pings == packets)