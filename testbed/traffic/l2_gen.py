from testbed.ns import (
    get_mac_addr,
)
from scapy.config import conf
from scapy.layers.inet import (
    Ether,
)
from testbed.traffic.layers import (
    GeneratorType,
    MonitoringInfo,
    UniformGeneratorInfo,
)
from testbed.traffic.utils import (
    scapy_reload,
)
import time
from typing import (
    Optional,
    Tuple,
)
from scapy.all import (hexdump, raw)

def _sock_and_header_without_ip(src_iface: str, dst_iface: Optional[str], dst_mac_addr: Optional[str]) -> Tuple:
    src_mac_addr = get_mac_addr(src_iface)
    packet_header = None
    if dst_mac_addr:
        packet_header = Ether(src=src_mac_addr, dst=dst_mac_addr)
    elif dst_iface:
        iface_mac_addr = get_mac_addr(dst_iface)
        packet_header = Ether(src=src_mac_addr, dst=iface_mac_addr)
    sock = conf.L2socket(iface=src_iface)
    return (sock, packet_header)


@scapy_reload
def uniform_gen(src_iface: str, dst_iface: Optional[str] = None, dst_mac_addr: Optional[str] = None, report = None, size=64, rate=1):
    seq = 0
    payload = "".join(["a" for _ in range(size)])
    sock, header = _sock_and_header_without_ip(src_iface, dst_iface, dst_mac_addr)
    monitoring_info = MonitoringInfo(gen=GeneratorType.UNIFORM)
    interval = 1.0/rate
    gen_info = UniformGeneratorInfo(inter=int(interval*1000))
    while True:
        monitoring_info.ts = int(time.time() * 1000) % (2 ** 32)
        monitoring_info.seq = seq
        seq += 1
        packet = header / monitoring_info / gen_info / payload
        sock.send(packet)
        time.sleep(interval)
