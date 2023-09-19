from gnuradio import (gr,
                      iio,
                      network,
                      pdu
                    )


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


class tun_in(gr.hier_block2):

    def __init__(self, iface, mtu, queue_size):
        gr.hier_block2.__init__(self, "tun_in",
                                gr.io_signature(0, 0, 0),
                                gr.io_signature(1, 1, gr.sizeof_char))
        self.tun = network.tuntap_pdu(iface, mtu, True)
        self.to_stream = pdu.pdu_to_stream_b(pdu.EARLY_BURST_APPEND, queue_size)
        self.msg_connect(self.tun, "pdus", self.to_stream, "pdus")
        self.connect(self.to_stream, self)

    def msg_in(self):
        return self.tun


class tun_out(gr.hier_block2):

    def __init__(self, iface, mtu, len_key):
        gr.hier_block2.__init__(self, "tun_out",
                                gr.io_signature(1, 1, gr.sizeof_char),
                                gr.io_signature(0, 0, 0),)
        self.tun = network.tuntap_pdu(iface, mtu, True)
        self.to_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, len_key)
        self.connect(self, self.to_pdu)
        self.msg_connect(self.to_pdu, "pdus", self.tun, "pdus")

    def msg_out(self):
        return self.tun


class tun_inout(gr.hier_block2):

    def __init__(self, iface, mtu, queue_size, len_key):
        gr.hier_block2.__init__(self, "tun_inout",
                                gr.io_signature(1, 1, gr.sizeof_char),
                                gr.io_signature(1, 1, gr.sizeof_char))
        self.tun = network.tuntap_pdu(iface, mtu, True)

        # IN
        self.to_stream = pdu.pdu_to_stream_b(pdu.EARLY_BURST_APPEND, queue_size)
        self.msg_connect(self.tun, "pdus", self.to_stream, "pdus")
        self.connect(self.to_stream, self)

        # OUT
        self.to_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, len_key)
        self.msg_connect( self.to_pdu, "pdus", self.tun, "pdus")
        self.connect(self, self.to_pdu)

    def msg_in(self):
        return self.tun