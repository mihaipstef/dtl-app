from app import sim

from gnuradio import (blocks,
                      dtl,
                      filter,
                      gr,
                      iio,
                      network,
                      pdu,)


# Real input over tun/tap interface and real channel using Pluto SDR
class ofdm_adaptive_real_tun_tx(gr.top_block):

    def __init__(self, config_dict, run_config_file):

        gr.top_block.__init__(
            self, "OFDM Adaptive Tx", catch_exceptions=True)

        self.run_config_file = run_config_file
        self.direct_carrier = config_dict.get("direct_carrier", 2400000000)
        self.feedback_carrier = config_dict.get("feedback_carrier", 850000000)
        self.data_bytes = config_dict.get("data_bytes", None)
        # Use TX default sample rate if not configured
        self.sample_rate = config_dict.get("sample_rate", dtl.ofdm_adaptive_config.ofdm_adaptive_tx_config.sample_rate)
        self.len_key = "len_key"


        self.tun0 = network.tuntap_pdu("tun0", 500, True)
        self.to_stream = pdu.pdu_to_stream_b(pdu.EARLY_BURST_DROP, 128)


        self.tx = dtl.ofdm_adaptive_tx.from_parameters(
            config_dict=config_dict["ofdm_config"],
            rolloff=0,
            scramble_bits=False,
            sample_rate=self.sample_rate,
            packet_length_tag_key=self.len_key,
        )
        print(f"sample_rate={self.tx.sample_rate}, direct_carrier={self.direct_carrier}")

        monitor_address = config_dict.get(
            "monitor_probe", "tcp://127.0.0.1:5556")
        monitor_probe_name = config_dict.get("monitor_probe_name", "probe")
        self.monitor_probe = dtl.zmq_probe(
            monitor_address, monitor_probe_name, bind=True)

        self.pluto_direct_sink = iio.fmcomms2_sink_fc32('ip:192.168.2.1' if 'ip:192.168.2.1' else iio.get_pluto_uri(), [True, True], 32768, False)
        self.pluto_direct_sink.set_len_tag_key('')
        self.pluto_direct_sink.set_bandwidth(self.tx.sample_rate)
        self.pluto_direct_sink.set_frequency(self.direct_carrier)
        self.pluto_direct_sink.set_samplerate(self.tx.sample_rate)
        self.pluto_direct_sink.set_attenuation(0, 20.0)
        self.pluto_direct_sink.set_filter_params('Auto', '', 0, 0)

        self.pluto_feedback_src = iio.fmcomms2_source_fc32('ip:192.168.2.1' if 'ip:192.168.2.1' else iio.get_pluto_uri(), [True, True], 32768)
        self.pluto_feedback_src.set_len_tag_key(self.len_key)
        self.pluto_feedback_src.set_frequency(self.feedback_carrier)
        self.pluto_feedback_src.set_samplerate(self.tx.sample_rate)
        self.pluto_feedback_src.set_gain_mode(0, 'manual')
        self.pluto_feedback_src.set_gain(0, 10)
        self.pluto_feedback_src.set_quadrature(True)
        self.pluto_feedback_src.set_rfdc(True)
        self.pluto_feedback_src.set_bbdc(True)
        self.pluto_feedback_src.set_filter_params('Auto', '', 0, 0)

        self.clipping_control = blocks.multiply_const_cc(config_dict.get("clipping_amp", 0.02))


    def wire_it(self):

        # Direct path
        self.msg_connect(self.tun0, "pdus", self.to_stream, "pdus")
        if self.data_bytes is None:
            self.connect((self.to_stream, 0), (self.tx, 0),  self.clipping_control,
                    filter.rational_resampler_ccc(
                        interpolation=1,
                        decimation=1,
                        taps=[],
                        fractional_bw=0.49),
                    self.pluto_direct_sink)
        else:
            self.connect((self.to_stream, 0), blocks.head(
                gr.sizeof_char, self.data_bytes), (self.tx, 0), self.clipping_control, 
                filter.rational_resampler_ccc(
                    interpolation=1,
                    decimation=1,
                    taps=[],
                    fractional_bw=0.49),
                self.pluto_direct_sink)

        # Feedback path
        self.connect(self.pluto_feedback_src,
            (self.tx, 1))

        # monitor and debug

        self.msg_connect((self.tx, "monitor"), (blocks.message_debug(), "store"))
        self.msg_connect(self.tun0, "pdus", blocks.message_debug(), "print")

        return self


class ofdm_adaptive_real_tun_rx(gr.top_block):

    def __init__(self, config_dict, run_config_file):
        gr.top_block.__init__(
            self, "OFDM Adaptive Tx", catch_exceptions=True)

        self.run_config_file = run_config_file
        self.direct_carrier = config_dict.get("direct_carrier", 2100000000)
        self.feedback_carrier = config_dict.get("feedback_carrier", 850000000)
        # Use TX default sample rate if not configured
        self.samp_rate = config_dict.get("sample_rate", dtl.ofdm_adaptive_config.ofdm_adaptive_tx_config.sample_rate)
        self.len_key = "len_key"

        self.rx = dtl.ofdm_adaptive_rx.from_parameters(
            config_dict=config_dict["ofdm_config"],
            rolloff=0,
            scramble_bits=False,
            packet_length_tag_key=self.len_key,
        )

        self.tun1 = network.tuntap_pdu("tun1", 500, True)
        self.to_pdu = pdu.tagged_stream_to_pdu(gr.types.byte_t, self.rx.packet_length_tag_key)

        monitor_address = config_dict.get(
            "monitor_probe", "tcp://127.0.0.1:5555")
        monitor_probe_name = config_dict.get("monitor_probe_name", "probe")
        self.monitor_probe = dtl.zmq_probe(
            monitor_address, monitor_probe_name, bind=True)

        self.pluto_direct_src = iio.fmcomms2_source_fc32('ip:192.168.3.1' if 'ip:192.168.3.1' else iio.get_pluto_uri(), [True, True], 32768)
        self.pluto_direct_src.set_len_tag_key(self.len_key)
        self.pluto_direct_src.set_frequency(self.direct_carrier)
        self.pluto_direct_src.set_samplerate(self.samp_rate)
        self.pluto_direct_src.set_gain_mode(0, 'slow_attack')
        self.pluto_direct_src.set_gain(0, 30)
        self.pluto_direct_src.set_quadrature(True)
        self.pluto_direct_src.set_rfdc(True)
        self.pluto_direct_src.set_bbdc(True)
        self.pluto_direct_src.set_filter_params('Auto', '', 0, 0)

        self.pluto_feedback_sink = iio.fmcomms2_sink_fc32('ip:192.168.3.1' if 'ip:192.168.3.1' else iio.get_pluto_uri(), [True, True], 32768, False)
        self.pluto_feedback_sink.set_len_tag_key('')
        self.pluto_feedback_sink.set_bandwidth(self.samp_rate)
        self.pluto_feedback_sink.set_frequency(self.feedback_carrier)
        self.pluto_feedback_sink.set_samplerate(self.samp_rate)
        self.pluto_feedback_sink.set_attenuation(0, 10.0)
        self.pluto_feedback_sink.set_filter_params('Auto', '', 0, 0)


    def wire_it(self):

        # Direct path
        self.connect(self.pluto_direct_src, (self.rx, 0), self.to_pdu)
        self.msg_connect(self.to_pdu, "pdus", self.tun1, "pdus")

        # Feedback path
        self.connect(
            (self.rx, 1), self.pluto_feedback_sink)

        # monitor and debug
        self.connect((self.rx, 0), blocks.null_sink(gr.sizeof_char))
        self.connect((self.rx, 2), blocks.null_sink(gr.sizeof_char))
        self.connect((self.rx, 5), blocks.null_sink(gr.sizeof_gr_complex))
        self.msg_connect((self.rx, "monitor"),
                         (blocks.message_debug(True), "store"))
        self.msg_connect((self.rx, "monitor"), (self.monitor_probe, "in"))
        self.msg_connect(self.to_pdu, "pdus", blocks.message_debug(), "print")

        return self
