import datetime as dt
from scapy.config import conf
from scapy.layers.inet import (
    ICMP,
    IP,
    IPOption_Timestamp,
)
from scapy.sendrecv import (
    sr1,
    send,
    sniff,
)


def scapy_reload(f):
    def wrap(*args, **kwargs):
        conf.ifaces.reload()
        conf.route.resync()
        f(*args, **kwargs)
    return wrap


@scapy_reload
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


@scapy_reload
def icmp_gen(collection, dst_ip_addr, size=64, ping_rate=1):
    seq = 0
    payload = "".join(["a" for _ in range(size)])
    while True:
        ts = int(dt.datetime.utcnow().timestamp()*1000) % (2 ** 32)
        packet = IP(dst=dst_ip_addr, ttl=64, options=IPOption_Timestamp(flg=0, timestamp=ts)) / ICMP(seq=seq, id=100) / payload
        seq += 1
        ans = send(packet, inter=1.0/ping_rate, verbose=0)


@scapy_reload
def icmp_sniff(collection, src_ip_addr, dst_iface, verbose=False):
    expected_seq = None
    lost_packets = 0
    packet_error_rate = 0
    while True:
        packets = sniff(iface=dst_iface, filter=f"icmp", count=1)
        ts = int(dt.datetime.utcnow().timestamp()*1000) % (2 ** 32)
        packet = packets[0]
        latency = None
        if ICMP not in packet or packet[ICMP].seq is None and packet[ICMP].id != 100:
            continue
        if len(packet[IP].options) == 1 and getattr(packet[IP].options[0], "timestamp", None) is not None:
            sent_ts = packet[IP].options[0].timestamp
            if sent_ts > ts:
                latency = 2 ** 32 + ts - sent_ts
            else:
                latency = ts - sent_ts

        if expected_seq is not None:
            lost_packets += packet[ICMP].seq - expected_seq
            packet_error_rate = 100 * lost_packets / packet[ICMP].seq
        expected_seq = packet[ICMP].seq + 1
        if verbose:
            print(f"ICMP: {packet[IP].src} --> {packet[IP].dst}, seq={packet[ICMP].seq}"
                f", expected_seq={expected_seq}, one_way_latency={latency}ms"
                f", packet_error_rate={packet_error_rate}%"
                f", sent_ts={sent_ts}, ts={ts}")
        if collection is not None and latency is not None:
            collection.insert_one({"probe_name": "icmp_ping", "insert_ts": dt.datetime.utcnow(),
                                   "one_way_latency": latency, "lost_packets": lost_packets, "packet_error_rate": packet_error_rate})
