import argparse
import json
from testbed import (
    app,
    env,
    monitoring,
    ns,
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

class _capture_stdout():
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


def _run_app(log_store_fname, dtl_app, config, config_file):
    with _capture_stdout(log_store_fname) as _:
        app.run(dtl_app=dtl_app, config_dict=config,
                    run_config_file=config_file)


def _run_in_env(env_name, f, *args, **kwargs):
    @ns.dtl_env(env_name)
    def __in_env_f(*a, **kw):
        f(*a, **kw)
    p = multiprocessing.Process(target=__in_env_f, args=args, kwargs=kwargs)
    p.start()
    return p


def run(app_name, config, env_name):
    logs_folder = env.log_path(env_name)
    config_file = config
    dtl_app = getattr(sim, app_name, None)
    if dtl_app is None:
        dtl_app = getattr(simplex, app_name, sim.ofdm_adaptive_sim_src)

    logs_store = f"{logs_folder}"

    # Load flow config
    cfg = {}
    with open(config_file, "r") as f:
        content = f.read()
        cfg = json.loads(content)

        run_timestamp = int(time.time())
        run_timestamp = 0

        name = cfg.get("name", uuid.uuid4())
        env_cfg = env.load_config(env_name)
        db_url = env_cfg.get("monitor_db", None)
        probe_url = env_cfg.get("monitor_probe", None)

        monitor_process = None
        monitor_process_pid = None
        collection_name = f"{name}_{run_timestamp}"
        collection = None
        if db_url:
            db_client = pymongo.MongoClient(db_url)
            db = db_client["probe_data"]
            collection = db[collection_name]
            if probe_url:
                monitor_process =  _run_in_env(env_name, monitoring.start_collect, probe_url, db, collection_name)
                monitor_process_pid = monitor_process.pid

        log_store_fname = f"{logs_store}/{name}_{run_timestamp}.log"

        try:
            app_config = cfg["app_config"]

            app_config["name"] = cfg["name"]

            app_proccess = _run_in_env(env_name, _run_app, log_store_fname=log_store_fname, dtl_app=dtl_app, config=app_config, config_file=config_file)
            #run_ofdm(**{"log_store_fname": log_store_fname, "dtl_app": dtl_app, "app_config": app_config, "config_file": experiments_file})

            traffic_generator = cfg.get("traffic_generator", None)
            traffic_generator_process = None
            traffic_generator_pid = None

            if traffic_generator:
                tr_func = getattr(traffic_generators, traffic_generator["func"])
                if tr_func:
                    args = traffic_generator["kwargs"]
                    args["collection"] = collection
                    traffic_generator_process = _run_in_env(env_name, tr_func, **args)
                    traffic_generator_pid = traffic_generator_process.pid

            traffic_sniffer = cfg.get("traffic_sniffer", None)
            traffic_sniffer_process = None
            traffic_sniffer_pid = None

            if traffic_sniffer:
                tr_func = getattr(traffic_generators, traffic_sniffer["func"])
                if tr_func:
                    args = traffic_sniffer["kwargs"]
                    args["collection"] = collection
                    traffic_sniffer_process =  _run_in_env(env_name, tr_func, **args)
                    traffic_sniffer_pid = traffic_sniffer_process.pid

            print(
                f"Running flow {name} PID: {app_proccess.pid}, monitoring PID: {monitor_process_pid}"
                f", traffic gen PID: {traffic_generator_pid}, traffic collect PID: {traffic_sniffer_pid}")

            while True:
                pass

        except KeyboardInterrupt as _:
            if monitor_process and monitor_process.is_alive():
                monitor_process.terminate()
            if app_proccess and app_proccess.is_alive():
                app_proccess.terminate()
            if traffic_generator_process and traffic_generator_process.is_alive():
                traffic_generator_process.terminate()
            if traffic_sniffer_process and traffic_sniffer_process.is_alive():
                traffic_sniffer_process.terminate()
            time.sleep(1)

        except Exception as ex:
            print("App failed")
            print(str(ex))
            print(traceback.format_exc())
