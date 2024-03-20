from .icmp_gen import (
    icmp_gen,
    icmp_ping,
)
from .icmp_sniff_reports import (
    IcmpPingReport,
    IcmpSniffReport,
)
from .l2_gen import (
    uniform_gen,
)
from .l2_sniff_reports import (
    L2SniffReport,
)
from .layers import (
    MonitoringInfo
)
from .sniff import (
    sniff,
)


from scapy.config import conf

def scapy_reload(f):
    def wrap(*args, **kwargs):
        conf.ifaces.reload()
        conf.route.resync()
        conf.use_pcap = False
        f(*args, **kwargs)
    return wrap
