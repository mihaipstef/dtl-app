import datetime as dt
from scapy.compat import raw
from scapy.layers.inet import (
    Ether,
)
from scapy.packet import (
    Packet,
    Raw,
)
from testbed.traffic.sniff import (
    SniffReport,
)
from testbed.traffic.layers import MonitoringInfo
from typing import (
    Optional
)


class L2SniffReport(SniffReport):

    def __init__(self, _db, _stdout):
        super().__init__(_db, _stdout)
        self.lost_packets = 0
        self.expected_seq = None
        self.packet_error_rate = 0


    def parse(self, rcvd_pkt: Packet, _: Optional[Packet] = None) -> Optional[dict]:
        if Ether not in rcvd_pkt:
            return None
        try:
            monitor_pkt = MonitoringInfo(raw(rcvd_pkt[Raw]))[MonitoringInfo]
        except:
            return None
        rcvd_ts = rcvd_pkt.time * 1000  % (2 ** 32)
        sent_ts = monitor_pkt.ts
        seq = monitor_pkt.seq
        latency = rcvd_ts - sent_ts
        if self.expected_seq is not None:
            self.lost_packets += seq - self.expected_seq
            if seq:
                self.packet_error_rate = 100 * self.lost_packets / seq
        self.expected_seq = seq + 1
        return {
            "probe_name": "l2_sniff",
            "time": dt.datetime.utcnow(),
            "one_way_latency": latency,
            "lost_packets": self.lost_packets,
            "packet_error_rate": self.packet_error_rate,
        }
