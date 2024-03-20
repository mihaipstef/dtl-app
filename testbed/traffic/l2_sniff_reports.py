import datetime as dt
from scapy.compat import raw
from scapy.layers.inet import (
    Ether,
)
from scapy.packet import (
    Packet,
    Raw,
)
import statistics
from testbed.traffic.sniff import (
    SniffReport,
)
from testbed.traffic.layers import (
    MonitoringInfo,
    generator_packet_cls,
)
from typing import (
    Optional
)


class L2SniffReport(SniffReport):

    def __init__(self, _db, _stdout):
        super().__init__(_db, _stdout)
        self.lost_packets = 0
        self.expected_seq = None
        self.packet_error_rate = 0
        self.last_pkt_ts = None
        self.intervals = []
        self.tx_interval = None

    def parse(self, rcvd_pkt: Packet, _: Optional[Packet] = None) -> Optional[dict]:
        if Ether not in rcvd_pkt:
            return None
        try:
            raw_payload = raw(rcvd_pkt[Raw])
            monitor_pkt = MonitoringInfo(raw_payload)[MonitoringInfo]
            raw_payload = raw(monitor_pkt[Raw])
            gen_info_pkt_cls = generator_packet_cls[monitor_pkt.gen]
            gen_info = None
            if gen_info_pkt_cls:
                gen_info = gen_info_pkt_cls(raw_payload)[gen_info_pkt_cls]
        except:
            return None
        rcvd_ts = rcvd_pkt.time * 1000  % (2 ** 32)
        sent_ts = monitor_pkt.ts
        seq = monitor_pkt.seq
        self.tx_interval = gen_info.inter

        # Latency
        latency = rcvd_ts - sent_ts
        # Jitter
        jitter = 0
        if self.last_pkt_ts is not None:
            i = (rcvd_ts - self.last_pkt_ts) / (seq - self.expected_seq + 1)
            self.intervals.append(i)
            if len(self.intervals) >= 100:
                self.intervals = self.intervals[1:]
            if len(self.intervals) >= 2:
                jitter = statistics.stdev(self.intervals)
        self.last_pkt_ts = rcvd_ts

        # Packet error rate
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
            "jitter": jitter
        }
