import datetime as dt
from scapy.config import conf
from scapy.layers.inet import (
    Ether,
    ICMP,
    IP,
    IPOption_Timestamp,
)
from scapy.packet import (
    Packet,
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
from testbed.traffic.utils import (
    scapy_reload,
)
import time
from typing import (
    Optional,
    Tuple,
)


def _sock_and_header_with_ip(dst_ip_addr: str) -> Tuple:
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
def icmp_gen(dst_ip_addr, report = None, size=64, ping_rate=1):
    seq = 0
    payload = "".join(["a" for _ in range(size)])
    sock, header = _sock_and_header_with_ip(dst_ip_addr)
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
def icmp_ping(dst_ip_addr, report, size=64, ping_rate=1, packets=None):
    sent = 0
    rcv = 0
    seq = 0
    sock, packet_header = _sock_and_header_with_ip(dst_ip_addr)
    payload = "".join(["a" for _ in range(size)])
    while packets is None or (packets is not None and sent < packets):
        packet = packet_header / ICMP(seq=seq, id=100) / payload
        seq += 1
        result =  sndrcv(sock, packet, timeout=3, inter=1.0/ping_rate, verbose=0)
        sent += 1
        if (result and
            len(result) and (r0:=result[0]) and
            len(r0) and (r00:=r0[0]) and
            len(r00) >= 1):
            if r00[1]:
                report.report(r00[1], packet)
                rcv += 1
