from enum import IntEnum
from scapy.fields import (
    IntField,
    IntEnumField,
)
from scapy.packet import Packet


class GeneratorType(IntEnum):
    NOT_SET = 0
    UNIFORM = 1


class MonitoringInfo(Packet):
    name = "MonitoringInfo"
    fields_desc=[
        IntField("ts", default=0),
        IntField("seq", default=0),
        IntEnumField("gen", GeneratorType.NOT_SET, GeneratorType)
    ]


class UniformGeneratorInfo(Packet):
    name = "UniformGeneratorInfo"
    fields_desc=[
        IntField("inter", default=1000),
    ]


generator_packet_cls = {
    GeneratorType.NOT_SET: None,
    GeneratorType.UNIFORM: UniformGeneratorInfo,
}