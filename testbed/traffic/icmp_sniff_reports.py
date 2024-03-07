import datetime as dt
from scapy.layers.inet import (
    Ether,
    ICMP,
    IP,
    IPOption_Timestamp,
)
from scapy.packet import (
    Packet,
)
from testbed.traffic.sniff import (
    SniffReport,
)
from typing import (
    Optional
)

class IcmpSniffReport(SniffReport):

    def __init__(self, _db, _stdout):
        super().__init__(_db, _stdout)
        self.lost_packets = 0
        self.expected_seq = None
        self.packet_error_rate = 0

    def parse(self, rcvd_pkt: Packet, _: Optional[Packet] = None) -> Optional[dict]:
        ts = rcvd_pkt.time * 1000  % (2 ** 32)
        latency = None
        if ICMP not in rcvd_pkt or rcvd_pkt[ICMP].seq is None or rcvd_pkt[ICMP].id != 100:
            return None
        sent_ts = None
        if len(rcvd_pkt[IP].options) == 1 and getattr(rcvd_pkt[IP].options[0], "timestamp", None) is not None:
            sent_ts = rcvd_pkt[IP].options[0].timestamp
            if sent_ts > ts:
                latency = 2 ** 32 + ts - sent_ts
            else:
                latency = ts - sent_ts

        if self.expected_seq is not None:
            self.lost_packets += rcvd_pkt[ICMP].seq - self.expected_seq
            self.packet_error_rate = 100 * self.lost_packets / rcvd_pkt[ICMP].seq
        self.expected_seq = rcvd_pkt[ICMP].seq + 1
        return {
            "probe_name": "icmp_ping",
            "time": dt.datetime.utcnow(),
            "one_way_latency": latency,
            "lost_packets": self.lost_packets,
            "packet_error_rate": self.packet_error_rate,
        }


class IcmpPingReport(SniffReport):

    def __init__(self, _db, _stdout):
        super().__init__(_db, _stdout)

    def parse(self, rcvd_pkt: Packet, sent_pkt: Optional[Packet] = None) -> Optional[dict]:
        if sent_pkt:
            t = rcvd_pkt.time - sent_pkt.sent_time
            return {"probe_name": "icmp_ping_time", "time": dt.datetime.utcnow(), "ping_time": t * 1000}
        return None
