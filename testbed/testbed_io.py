from gnuradio import (gr,
                      iio,
                      network,
                      pdu,
                      testbed,
                    )
from testbed.ns import (
    get_tuntap_type,
    get_mac_addr,
)
from testbed.wrap import D

class pluto_in(gr.hier_block2):

    def __init__(self, uri, sample_rate, carrier, len_key, buffer_size, gain=None):
        gr.hier_block2.__init__(self, "pluto_in",
                                gr.io_signature(0, 0, 0),
                                gr.io_signature(1, 1, gr.sizeof_gr_complex))
        self.pluto_src = iio.fmcomms2_source_fc32(uri, [True, True], buffer_size)
        self.pluto_src.set_len_tag_key(len_key)
        self.pluto_src.set_frequency(carrier)
        self.pluto_src.set_samplerate(sample_rate)
        if gain is None:
            self.pluto_src.set_gain_mode(0, 'slow_attack')
        else:
            self.pluto_src.set_gain_mode(0, 'manual')
            self.pluto_src.set_gain(0, gain)
        self.pluto_src.set_quadrature(True)
        self.pluto_src.set_rfdc(True)
        self.pluto_src.set_bbdc(True)
        self.pluto_src.set_filter_params('Auto', '', 0, 0)
        self.connect(self.pluto_src, self)

    def get(self):
        return self.pluto_src


class pluto_out(gr.hier_block2):

    def __init__(self, uri, sample_rate, carrier, len_key, buffer_size, att):
        gr.hier_block2.__init__(self, "pluto_out",
                                gr.io_signature(1, 1, gr.sizeof_gr_complex),
                                gr.io_signature(0, 0, 0))
        self.pluto_sink = iio.fmcomms2_sink_fc32(uri, [True, True], buffer_size, False)
        self.pluto_sink.set_len_tag_key(len_key)
        self.pluto_sink.set_bandwidth(sample_rate)
        self.pluto_sink.set_frequency(carrier)
        self.pluto_sink.set_samplerate(sample_rate)
        self.pluto_sink.set_attenuation(0, att)
        self.pluto_sink.set_filter_params('Auto', '', 0, 0)
        self.connect(self, self.pluto_sink)

    def get(self):
        return self.pluto_sink


class tun_io(gr.hier_block2):

    def __init__(self, iface, mtu, queue_size, len_key):
        gr.hier_block2.__init__(self, "tun_io",
                                gr.io_signature(1, 1, gr.sizeof_char),
                                gr.io_signature(1, 1, gr.sizeof_char))

        self.hb = D(self, self)
        self.tun = D(self, network.tuntap_pdu, iface, mtu, True)
        self.ip_validator = testbed.ip_validator("")
        self.from_phy = D(self, testbed.from_phy, testbed.transported_protocol_t.IPV4_ONLY, self.ip_validator, len_key)

        # IN (to TX)
        self.to_phy = D(self, testbed.to_phy, testbed.transported_protocol_t.IPV4_ONLY, len_key)
        self.tun.pdus >> self.to_phy.pdus
        self.to_phy  >> self.hb

        # OUT (from RX)
        self.to_pdu = D(self, pdu.tagged_stream_to_pdu, gr.types.byte_t, len_key)
        self.to_pdu.pdus >> self.tun.pdus
        self.hb >> self.from_phy >> self.to_pdu


class tap_io(gr.hier_block2):

    def __init__(self, iface, mtu, queue_size, len_key, protocol):
        gr.hier_block2.__init__(self, "tap_io",
                                gr.io_signature(1, 1, gr.sizeof_char),
                                gr.io_signature(1, 1, gr.sizeof_char))

        self.hb = D(self, self)
        self.tap = D(self, network.tuntap_pdu, iface, mtu, False)
        if protocol == testbed.transported_protocol_t.MODIFIED_ETHER:
            validator = testbed.modified_ethernet_validator(get_mac_addr(iface))
        else:
            validator = testbed.ethernet_validator(get_mac_addr(iface))
        self.from_phy = D(self, testbed.from_phy, protocol, validator, len_key)

        # IN (to TX)
        self.to_phy = D(self, testbed.to_phy, protocol, len_key)
        self.tap.pdus >> self.to_phy.pdus
        self.to_phy >> self.hb

        # OUT (from RX)
        self.to_pdu = D(self, pdu.tagged_stream_to_pdu, gr.types.byte_t, len_key)
        self.to_pdu.pdus >> self.tap.pdus
        self.hb >> self.from_phy >> self.to_pdu


class tuntap:

    def __new__(cls, iface, mtu, queue_size, len_key, protocol):
        match get_tuntap_type(iface):
            case 1:
                return tun_io(iface, mtu, queue_size, len_key)
            case 2:
                return tap_io(iface, mtu, queue_size, len_key, protocol)
            case _:
                raise Exception("unknown interface")