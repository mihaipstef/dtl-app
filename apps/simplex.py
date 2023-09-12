from testbed import (
    app,
    testbed_io,
)

from gnuradio import (blocks,
                      dtl,
                      filter,
                      gr,
                      iio,
                      network,
                      pdu,)


# Real input over tun/tap interface and real channel using Pluto SDR
class ofdm_adaptive_simplex_tx(app.dtl_app):

    def __init__(self, config_dict, run_config_file):

        app.dtl_app.__init__(
            self, config_dict, run_config_file)

        self.direct_carrier = config_dict.get("direct_carrier", 2400000000)
        self.feedback_carrier = config_dict.get("feedback_carrier", 850000000)
        self.data_bytes = config_dict.get("data_bytes", None)
        self.direct_tun = config_dict.get("direct_tun", "tun0")
        self.direct_uri = config_dict.get("direct_uri", "ip:192.168.2.1")
        self.feedback_uri = config_dict.get("feedback_uri", "ip:192.168.3.1")
        # Use TX default sample rate if not configured
        self.sample_rate = config_dict.get("sample_rate", dtl.ofdm_adaptive_config.ofdm_adaptive_tx_config.sample_rate)
        self.len_key = "len_key"


        self.data_input = testbed_io.tun_in("tun0", 500, 128)
        self.data_output = testbed_io.pluto_out('ip:192.168.2.1' if 'ip:192.168.2.1' else iio.get_pluto_uri(), self.sample_rate, self.direct_carrier, self.len_key, 32768)
        self.feedback_in = testbed_io.pluto_in('ip:192.168.2.1' if 'ip:192.168.2.1' else iio.get_pluto_uri(), self.sample_rate, self.feedback_carrier, self.len_key, 32768)

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

        self.clipping_control = blocks.multiply_const_cc(config_dict.get("clipping_amp", 0.02))


    def wire_it(self):

        # Direct path
        if self.data_bytes is None:
            self.connect((self.data_input, 0), (self.tx, 0),  self.clipping_control,
                    filter.rational_resampler_ccc(
                        interpolation=1,
                        decimation=1,
                        taps=[],
                        fractional_bw=0.49),
                    self.data_output)
        else:
            self.connect((self.data_input, 0), blocks.head(
                gr.sizeof_char, self.data_bytes), (self.tx, 0), self.clipping_control, 
                filter.rational_resampler_ccc(
                    interpolation=1,
                    decimation=1,
                    taps=[],
                    fractional_bw=0.49),
                self.data_output)

        # Feedback path
        self.connect(self.feedback_in,
            (self.tx, 1))

        # monitor and debug
        self.msg_connect((self.tx, "monitor"), (blocks.message_debug(), "store"))

        return self


class ofdm_adaptive_simplex_rx(app.dtl_app):

    def __init__(self, config_dict, run_config_file):
        app.dtl_app.__init__(
            self, config_dict, run_config_file)

        self.run_config_file = run_config_file
        self.direct_carrier = config_dict.get("direct_carrier", 2100000000)
        self.feedback_carrier = config_dict.get("feedback_carrier", 850000000)
        self.direct_tun = config_dict.get("direct_tun", "tun1")
        self.direct_uri = config_dict.get("direct_uri", "ip:192.168.2.1")
        self.feedback_uri = config_dict.get("feedback_uri", "ip:192.168.3.1")

        # Use TX default sample rate if not configured
        self.samp_rate = config_dict.get("sample_rate", dtl.ofdm_adaptive_config.ofdm_adaptive_tx_config.sample_rate)
        self.len_key = "len_key"

        self.rx = dtl.ofdm_adaptive_rx.from_parameters(
            config_dict=config_dict["ofdm_config"],
            rolloff=0,
            scramble_bits=False,
            packet_length_tag_key=self.len_key,
        )

        self.data_out = testbed_io.tun_out(self.direct_tun, 500, self.len_key)
        self.data_in = testbed_io.pluto_in(self.direct_uri, self.sample_rate, self.direct_carrier, self.len_key, 32768)
        self.feedback_out = testbed_io.pluto_in(self.feedback_uri, self.sample_rate, self.feedback_carrier, self.len_key, 32768)

        monitor_address = config_dict.get(
            "monitor_probe", "tcp://127.0.0.1:5555")
        monitor_probe_name = config_dict.get("monitor_probe_name", "probe")
        self.monitor_probe = dtl.zmq_probe(
            monitor_address, monitor_probe_name, bind=True)


    def wire_it(self):

        # Direct path
        self.connect(self.data_in, (self.rx, 0), self.to_pdu)
        self.msg_connect(self.to_pdu, "pdus", self.tun1, "pdus")

        # Feedback path
        self.connect(
            (self.rx, 1), self.feedback_out)

        # monitor and debug
        self.connect((self.rx, 0), blocks.null_sink(gr.sizeof_char))
        self.connect((self.rx, 2), blocks.null_sink(gr.sizeof_char))
        self.connect((self.rx, 5), blocks.null_sink(gr.sizeof_gr_complex))
        self.msg_connect((self.rx, "monitor"),
                         (blocks.message_debug(True), "store"))
        self.msg_connect((self.rx, "monitor"), (self.monitor_probe, "in"))

        return self
