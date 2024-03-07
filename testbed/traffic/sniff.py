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
    sniff as scapy_sniff,
)
from testbed.db import (
    db_access,
)
from testbed.traffic.utils import (
    scapy_reload,
)
from typing import (
    Optional,
    Protocol,
)


class SniffReport:
    db: db_access
    stdout: bool
    sniff_dst: bool

    def __init__(self, _db, _stdout, _sniff_dst=True):
        self.db = _db
        self.stdout = _stdout
        self.sniff_dst = _sniff_dst

    def report(self, rcvd_pkt: Packet, sent_pkt: Optional[Packet] = None):
        if not rcvd_pkt:
            return
        rep = self.parse(rcvd_pkt, sent_pkt)
        if self.stdout:
            print(rep)
        if self.db and rep:
            self.db.write(
                self.db.prepare(rep))

    def parse(self, rcvd_pkt: Packet, sent_pkt: Optional[Packet] = None) -> Optional[dict]:...


@scapy_reload
def sniff(r: SniffReport, iface):
    while True:
        packet = scapy_sniff(iface=iface, filter=f"", count=1)[0]
        r.report(packet)
