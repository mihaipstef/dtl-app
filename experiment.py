#!/usr/bin/env python3

import argparse
import json
import experiment.monitoring as monitoring
import experiment.traffic_generators as traffic_generators
import multiprocessing
import os
import pymongo
import experiment.sim as sim
import sys
import time
import timeit
import traceback
import uuid


class capture_stdout():
    def __init__(self, log_fname):
        self.log_fname = log_fname
        sys.stdout.flush()
        self.log = os.open(self.log_fname, os.O_WRONLY |
                           os.O_TRUNC | os.O_CREAT)

    def __enter__(self):
        self.orig_stdout = os.dup(1)
        self.new_stdout = os.dup(1)
        os.dup2(self.log, 1)
        sys.stdout = os.fdopen(self.new_stdout, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.flush()
        os.dup2(self.orig_stdout, 1)
        os.close(self.orig_stdout)
        os.close(self.log)


def run_ofdm(log_store_fname, sim_cls, ofdm_config, config_file):
    with capture_stdout(log_store_fname) as _:
        sim.main(top_block_cls=sim_cls, config_dict=ofdm_config,
                 run_config_file=config_file)


parser = argparse.ArgumentParser()
parser.add_argument("--logs", type=str, default=".",
                    help="Logs and other artifacts location")
parser.add_argument("--config", type=str, default="config.json",
                    help="Experiment configuration json file")
parser.add_argument("--sim_cls", type=str, default="ofdm_adaptive_loopback_src",
                    help="Simulator class used for the experiment")

args = parser.parse_args()

logs_folder = args.logs
experiments_file = args.config
sim_cls = getattr(sim, args.sim_cls, sim.ofdm_adaptive_sim_src)

logs_store = f"{logs_folder}"
current_log = f"{logs_folder}/sim.log"

# Load experiments
experiments = []
with open(experiments_file, "r") as f:
    experimets_path = os.path.dirname(experiments_file)
    content = f.read()
    experiments = json.loads(content)
    for e in experiments:
        ofdm_cfg = e["ofdm_config"]
        if "fec_codes" in ofdm_cfg and len(ofdm_cfg["fec_codes"]):
            ofdm_cfg["fec_codes"] = [(name, f"{experimets_path}/{fn}")
                                     for name, fn in ofdm_cfg["fec_codes"]]

run_timestamp = int(time.time())
run_timestamp = 0

for i, e in enumerate(experiments):

    name = e.get("name", uuid.uuid4())

    if "skip" in e and e["skip"]:
        print(f"Skip experiment {name}, number: {i}")
        continue

    db_url = e.get("monitor_db", None)
    probe_url = e.get("monitor_probe", None)

    monitor_process = None
    monitor_process_pid = None
    collection_name = f"{name}_{run_timestamp}"
    collection = None
    if probe_url and db_url:
        db_client = pymongo.MongoClient(db_url)
        db = db_client["probe_data"]
        collection = db[collection_name]
        monitor_process = multiprocessing.Process(
            target=monitoring.start_collect, args=(probe_url, db, collection_name,))
        monitor_process.start()
        monitor_process_pid = monitor_process.pid

    log_store_fname = f"{logs_store}/experiment_{run_timestamp}_{name}.log"
    experiment_fname = f"{logs_store}/experiment_{run_timestamp}_{name}.json"
    with open(experiment_fname, "w") as f:
        f.write(json.dumps(e))

    try:
        ofdm_config = e["ofdm_config"]
        ofdm_config["name"] = e["name"]
        ofdm_process = multiprocessing.Process(
            target=run_ofdm, kwargs={"log_store_fname": log_store_fname, "sim_cls": sim_cls, "ofdm_config": ofdm_config, "config_file": experiments_file})
        ofdm_process.start()

        traffic_generator = e.get("traffic_generator", None)
        traffic_generator_process = None
        traffic_generator_pid = None

        if traffic_generator:
            tr_func = getattr(traffic_generators, traffic_generator["func"])
            if tr_func:
                args = traffic_generator["kwargs"]
                args["collection"] = collection
                print(args)
                traffic_generator_process = multiprocessing.Process(
                    target=tr_func, kwargs=args)
                traffic_generator_process.start()
                traffic_generator_pid = traffic_generator_process.pid
        print(
            f"Running experiment {name}, number: {i}, PID: {ofdm_process.pid}, monitoring PID: {monitor_process_pid}, traffic PID: {traffic_generator_pid}")

        while True:
            pass

    except KeyboardInterrupt as _:
        if monitor_process and monitor_process.is_alive():
            monitor_process.terminate()
        if ofdm_process and ofdm_process.is_alive():
            ofdm_process.terminate()
        time.sleep(1)

    except Exception as ex:
        print("experiment failed")
        print(str(ex))
        print(traceback.format_exc())
