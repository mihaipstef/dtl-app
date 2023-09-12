from app import sim
import json
import os
import signal

def run(
        top_block_cls=sim.ofdm_adaptive_sim_src,
        config_dict=None,
        run_config_file="experiments.json",):

    tb = top_block_cls(
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
