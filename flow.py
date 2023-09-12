#!/usr/bin/env python3

import argparse
import json
from testbed import (
    app,
    monitoring,
    traffic_generators,
)
from  apps import sim, simplex
import multiprocessing
import os
import pymongo
import sys
import time
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


def run_app(log_store_fname, dtl_app, config, config_file):
    with capture_stdout(log_store_fname) as _:
        app.run(dtl_app=dtl_app, config_dict=config,
                    run_config_file=config_file)


parser = argparse.ArgumentParser()
parser.add_argument("--logs", type=str, default=".",
                    help="Logs and other artifacts location")
parser.add_argument("--config", type=str, default="config.json",
                    help="Experiment configuration json file")
parser.add_argument("--dtl_app", type=str, default="ofdm_adaptive_loopback_src",
                    help="Simulator class used for the experiment")

args = parser.parse_args()

logs_folder = args.logs
config_file = args.config
dtl_app = getattr(sim, args.dtl_app, None)
if dtl_app is None:
    dtl_app = getattr(simplex, args.dtl_app, sim.ofdm_adaptive_sim_src)

logs_store = f"{logs_folder}"
current_log = f"{logs_folder}/sim.log"

# Load flow config
cfg = {}
with open(config_file, "r") as f:
    config_path = os.path.dirname(config_file)
    content = f.read()
    cfg = json.loads(content)
    ofdm_cfg = cfg["ofdm_config"]
    if "fec_codes" in ofdm_cfg and len(ofdm_cfg["fec_codes"]):
        ofdm_cfg["fec_codes"] = [(name, f"{config_path}/{fn}")
                                    for name, fn in ofdm_cfg["fec_codes"]]
    run_timestamp = int(time.time())
    run_timestamp = 0

    name = cfg.get("name", uuid.uuid4())
    db_url = cfg.get("monitor_db", None)
    probe_url = cfg.get("monitor_probe", None)

    monitor_process = None
    monitor_process_pid = None
    collection_name = f"{name}_{run_timestamp}"
    collection = None
    if db_url:
        db_client = pymongo.MongoClient(db_url)
        db = db_client["probe_data"]
        collection = db[collection_name]
        if probe_url:
            monitor_process = multiprocessing.Process(
                target=monitoring.start_collect, args=(probe_url, db, collection_name,))
            monitor_process.start()
            monitor_process_pid = monitor_process.pid

    log_store_fname = f"{logs_store}/experiment_{run_timestamp}_{name}.log"
    experiment_fname = f"{logs_store}/experiment_{run_timestamp}_{name}.json"
    with open(experiment_fname, "w") as f:
        f.write(json.dumps(cfg))

    try:
        ofdm_config = cfg["ofdm_config"]
        ofdm_config["name"] = cfg["name"]
        ofdm_process = multiprocessing.Process(
            target=run_app, kwargs={"log_store_fname": log_store_fname, "dtl_app": dtl_app, "config": cfg, "config_file": config_file})
        ofdm_process.start()
        #run_ofdm(**{"log_store_fname": log_store_fname, "dtl_app": dtl_app, "ofdm_config": ofdm_config, "config_file": experiments_file})

        traffic_generator = cfg.get("traffic_generator", None)
        traffic_generator_process = None
        traffic_generator_pid = None

        if traffic_generator:
            tr_func = getattr(traffic_generators, traffic_generator["func"])
            if tr_func:
                args = traffic_generator["kwargs"]
                args["collection"] = collection
                traffic_generator_process = multiprocessing.Process(
                    target=tr_func, kwargs=args)
                traffic_generator_process.start()
                traffic_generator_pid = traffic_generator_process.pid

        traffic_sniffer = cfg.get("traffic_sniffer", None)
        traffic_sniffer_process = None
        traffic_sniffer_pid = None

        if traffic_sniffer:
            tr_func = getattr(traffic_generators, traffic_sniffer["func"])
            if tr_func:
                args = traffic_sniffer["kwargs"]
                args["collection"] = collection
                traffic_sniffer_process = multiprocessing.Process(
                    target=tr_func, kwargs=args)
                traffic_sniffer_process.start()
                traffic_sniffer_pid = traffic_sniffer_process.pid

        print(
            f"Running flow {name} PID: {ofdm_process.pid}, monitoring PID: {monitor_process_pid}"
            f", traffic gen PID: {traffic_generator_pid}, traffic collect PID: {traffic_generator_pid}")

        while True:
            pass

    except KeyboardInterrupt as _:
        if monitor_process and monitor_process.is_alive():
            monitor_process.terminate()
        if ofdm_process and ofdm_process.is_alive():
            ofdm_process.terminate()
        if traffic_generator_process and traffic_generator_process.is_alive():
            traffic_generator_process.terminate()
        if traffic_sniffer_process and traffic_sniffer_process.is_alive():
            traffic_sniffer_process.terminate()
        time.sleep(1)

    except Exception as ex:
        print("flow failed")
        print(str(ex))
        print(traceback.format_exc())
