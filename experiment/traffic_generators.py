import datetime as dt
from scapy.layers.inet import (
    ICMP,
    IP,
)
from scapy.sendrecv import (
    sr1,
)


def icmp_ping(collection, ip_addr, size=64, ping_rate=1, verbose=False):
    sent = 0
    rcv = 0
    seq = 0
    payload = "".join(["a" for _ in range(size)])
    while True:
        packet = IP(dst=ip_addr, ttl=64) / ICMP(seq=seq, id=100) / payload
        seq += 1
        ans = sr1(packet, timeout=3, inter=1.0/ping_rate, verbose=0)
        sent += 1
        t = None
        if ans:
            t = ans.time - packet.sent_time
            if collection is not None:
                collection.insert_one({"probe_name": "icmp_ping_time", "insert_ts": dt.datetime.utcnow(), "time": t * 1000})
            rcv += 1
        if verbose:
            print(f"sent={sent}, received={rcv}, time={t}s")
        if collection is not None:
            collection.insert_one({"probe_name": "icmp_ping_failure", "insert_ts": dt.datetime.utcnow(), "fail_rate": 100 * (sent - rcv)/sent})