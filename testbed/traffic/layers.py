from scapy.fields import (
    IntField,
)
from scapy.packet import Packet

class MonitoringInfo(Packet):
    name = "MonitoringInfo"
    fields_desc=[
        IntField("ts", default=0),
        IntField("seq", default=0)
    ]
