import datetime as dt
from scapy.config import conf
from scapy.layers.inet import (
    Ether,
    ICMP,
    IP,
    IPOption_Timestamp,
)
from scapy.sendrecv import (
    srp1,
    sndrcv,
    sniff,
)
from testbed.arp import (
    get_arp_entry,
)
from testbed.ns import (
    get_mac_addr,
    get_tuntap_type,
)
import time


def scapy_reload(f):
    def wrap(*args, **kwargs):
        conf.ifaces.reload()
        conf.route.resync()
        conf.use_pcap = False
        f(*args, **kwargs)
    return wrap


def _sock_and_header(dst_ip_addr):
    l3_header = IP(dst=dst_ip_addr, ttl=64)
    try:
        ifname = l3_header.route()[0]
    except AttributeError:
        ifname = None

    sock = None
    packet_header = None
    if ifname:
        match get_tuntap_type(ifname):
            case 1:
                packet_header = l3_header
                sock = conf.L3socket(iface=ifname)
            case 2:
                src_mac_addr = get_mac_addr(ifname)
                dst_mac_addr = get_arp_entry(dst_ip_addr, ifname)
                packet_header = Ether(src=src_mac_addr, dst=dst_mac_addr) / l3_header
                sock = conf.L2socket(iface=ifname)
            case _:
                pass
    return (sock, packet_header)


@scapy_reload
def icmp_ping(db_access, dst_ip_addr, size=64, ping_rate=1, packets=None, verbose=False):
    sent = 0
    rcv = 0
    seq = 0
    sock, packet_header = _sock_and_header(dst_ip_addr)
    payload = "".join(["a" for _ in range(size)])
    while packets is None or (packets is not None and sent < packets):
        packet = packet_header / ICMP(seq=seq, id=100) / payload
        seq += 1
        result =  sndrcv(sock, packet, timeout=3, inter=1.0/ping_rate, verbose=0)
        sent += 1
        t = None
        if (result and
            len(result) and (r0:=result[0]) and
            len(r0) and (r00:=r0[0]) and
            len(r00) >= 1):
            ans = r00[1]
            if ans:
                db_access.write({"probe_name": "test"})
                t = ans.time - packet.sent_time
                if db_access is not None:
                    db_access.write({"probe_name": "icmp_ping_time", "time": dt.datetime.utcnow(), "ping_time": t * 1000})
                rcv += 1
        if verbose:
            print(f"sent={sent}, received={rcv}, time={t}s")
        if db_access is not None:
            db_access.write({"probe_name": "icmp_ping_failure", "time": dt.datetime.utcnow(), "fail_rate": 100 * (sent - rcv)/sent})


@scapy_reload
def icmp_gen(db_access, dst_ip_addr, size=64, ping_rate=1):
    seq = 0
    payload = "".join(["a" for _ in range(size)])
    sock, header = _sock_and_header(dst_ip_addr)
    l2_header = None
    if Ether in header:
        l2_header = header[Ether]
        l2_header.remove_payload()
    while True:
        ts = int(time.time() * 1000) % (2 ** 32)
        if l2_header:
            packet = l2_header / IP(dst=dst_ip_addr, ttl=64, options=IPOption_Timestamp(flg=0, timestamp=ts)) / ICMP(seq=seq, id=100) / payload
        else:
            packet = IP(dst=dst_ip_addr, ttl=64, options=IPOption_Timestamp(flg=0, timestamp=ts)) / ICMP(seq=seq, id=100) / payload
        seq += 1
        sock.send(packet)
        time.sleep(1.0/ping_rate)


@scapy_reload
def icmp_sniff(db_access, src_ip_addr, dst_iface, verbose=False):
    expected_seq = None
    lost_packets = 0
    packet_error_rate = 0
    
    while True:
        packet = sniff(iface=dst_iface, filter=f"", count=1)[0]
        ts = packet.time * 1000  % (2 ** 32)
        latency = None
        if ICMP not in packet or packet[ICMP].seq is None or packet[ICMP].id != 100:
            continue
        sent_ts = None
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
        if db_access is not None and latency is not None:
            db_access.write(
                db_access.prepare({
                    "probe_name": "icmp_ping",
                    "time": dt.datetime.utcnow(),
                    "one_way_latency": latency,
                    "lost_packets": lost_packets,
                    "packet_error_rate": packet_error_rate,
                })
            )
