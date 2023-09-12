from abc import ABC, abstractmethod
from gnuradio import (analog,
                      blocks,
                      channels,
                      dtl,
                      gr,
                      iio,
                      network,
                      pdu,)
import json
import signal


class dtl_app(ABC, gr.top_block):

    def __init__(self, config_dict, run_config_file):
        gr.top_block.__init__(
            self, "DTL app", catch_exceptions=True)
        self.run_config_file = run_config_file

    @abstractmethod
    def wire_it(self):
        ...


def run(
        dtl_app=dtl_app,
        config_dict=None,
        run_config_file="experiments.json",):

    tb = dtl_app(
        config_dict=config_dict,
        run_config_file=run_config_file,).wire_it()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

    # To update parameters on the fly:
    # - define attribute to ofdm_adaptive_sim, eg new_attr
    # - implement setter, eg. set_new_attr
    def config_update(sig=None, frame=None):
        try:
            # if "/" in tb.run_config_file:
            #     run_config_file = f"{tb.run_config_file}"
            # else:
            #     run_config_file = f"{os.path.dirname(__file__)}/{tb.run_config_file}"
            print(f"Load: {tb.run_config_file}")
            with open(tb.run_config_file, "r") as f:
                content = f.read()
                cfg = json.loads(content)
                for k, v in cfg["live_config"].items():
                    if (setter := getattr(tb, f"set_{k}", None)) and getattr(tb, k):
                        print(f"live config update {k}={v}")
                        setter(v)
        except Exception as ex:
            print(f"Config file not found or broken ({tb.run_config_file})")
            print(str(ex))

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGHUP, config_update)

    config_update()

    tb.run()
