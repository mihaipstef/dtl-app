import datetime as dt
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


def icmp_gen(collection, dst_ip_addr, size=64, ping_rate=1):
    seq = 0
    payload = "".join(["a" for _ in range(size)])
    while True:
        ts = int(dt.datetime.utcnow().timestamp()*1000) % (2 ** 32)
        packet = IP(dst=dst_ip_addr, ttl=64, options=IPOption_Timestamp(flg=0, timestamp=ts)) / ICMP(seq=seq, id=100) / payload
        seq += 1
        ans = send(packet, inter=1.0/ping_rate, verbose=0)


def icmp_sniff(collection, src_ip_addr, dst_iface, verbose=False):
    expected_seq = None
    lost_packets = 0
    packet_error_rate = None
    while True:
        packets = sniff(iface=dst_iface, filter=f"icmp", count=1)
        ts = int(dt.datetime.utcnow().timestamp()*1000) % (2 ** 32)
        packet = packets[0]
        latency = None
        if len(packet[IP].options) == 1:
            latency = ts - int(packet[IP].options[0].timestamp)
        if expected_seq is None:
            expected_seq = packet[ICMP].seq
        else:
            lost_packets += packet[ICMP].seq - expected_seq
            packet_error_rate = 100 * lost_packets / packet[ICMP].seq
        if verbose:
            print(f"ICMP: {packet[IP].src} --> {packet[IP].dst}, seq={packet[ICMP].seq}"
                f", expected_seq={expected_seq}, one_way_latency={latency}ms"
                f", packet_error_rate={packet_error_rate}%")
        if collection is not None:
            print(collection)
            collection.insert_one({"probe_name": "icmp_ping_failure", "insert_ts": dt.datetime.utcnow(),
                                   "one_way_latency": latency, "lost_packets": lost_packets, "packet_error_rate": packet_error_rate})
        expected_seq = packet[ICMP].seq + 1
