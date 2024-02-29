import datetime as dt
import enum
import json
from testbed import (
    app,
    db,
    env,
    monitoring,
    ns,
    traffic_generators,
)
from  apps import sim, simplex
import multiprocessing
import os
import psutil as ps
import pymongo
import sys
import time
import traceback
import uuid


class stop_condition(enum.Enum):
    WHEN_TRAFFIC_DONE = 0
    WHEN_APP_DONE = 1


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
    def __in_env_f(*a, **kw):
        ns.set_env_for_proccess(env_name)
        f(*a, **kw)
    p = multiprocessing.Process(target=__in_env_f, args=args, kwargs=kwargs)
    p.start()
    return p


def run_app(app, cfg, env_name, env_cfg, config_file=None):
    db_config = env_cfg.get("monitor_db", None)
    probe_url = env_cfg.get("monitor_probe", None)

    name = cfg.get("name", uuid.uuid4())

    logs_store = env_cfg.get("logs", "/tmp")

    show_cpu = cfg.get("show_cpu", False)

    monitor_process = None
    monitor_process_pid = None
    collection_name = f"{name}"
    db_access = None
    if db_config:
        db_access = db.db(**db_config, name=collection_name)
        if probe_url:
            monitor_process =  _run_in_env(env_name, monitoring.start_collect_batch, probe_url, db_access, 1000)
            monitor_process_pid = monitor_process.pid

    log_store_fname = f"{logs_store}/{name}.log"

    try:
        app_config = cfg["app_config"]
        stop_cnd = cfg.get("stop_condition", stop_condition.WHEN_APP_DONE)

        app_config["name"] = cfg["name"]
        app_config["env_mode"] = env_cfg["mode"]

        app_proccess = _run_in_env(env_name, _run_app, log_store_fname=log_store_fname, dtl_app=app, config=app_config, config_file=config_file)
        #run_ofdm(**{"log_store_fname": log_store_fname, "dtl_app": dtl_app, "app_config": app_config, "config_file": experiments_file})

        time.sleep(1)

        traffic_generator = cfg.get("traffic_generator", None)
        traffic_generator_process = None
        traffic_generator_pid = None

        if traffic_generator:
            tr_func = getattr(traffic_generators, traffic_generator["func"])
            if tr_func:
                args = traffic_generator["kwargs"]
                args["db_access"] = db_access
                traffic_generator_process = _run_in_env(env_name, tr_func, **args)
                traffic_generator_pid = traffic_generator_process.pid

        traffic_sniffer = cfg.get("traffic_sniffer", None)
        traffic_sniffer_process = None
        traffic_sniffer_pid = None

        if traffic_sniffer:
            tr_func = getattr(traffic_generators, traffic_sniffer["func"])
            if tr_func:
                args = traffic_sniffer["kwargs"]
                args["db_access"] = db_access
                traffic_sniffer_process =  _run_in_env(env_name, tr_func, **args)
                traffic_sniffer_pid = traffic_sniffer_process.pid

        print(
            f"Running flow {name} PID: {app_proccess.pid}, monitoring PID: {monitor_process_pid}"
            f", traffic gen PID: {traffic_generator_pid}, traffic collect PID: {traffic_sniffer_pid}")

        try:
            app_ps = ps.Process(app_proccess.pid)
            broker_ps = ps.Process(monitor_process.pid)
        except:
            raise KeyboardInterrupt()

        total_app_cpu = 0
        total_broker_cpu = 0
        count = 0
        while True:

            match (stop_cnd):
                case stop_condition.WHEN_APP_DONE:
                    if not app_ps.is_running():
                        raise KeyboardInterrupt()
                case stop_condition.WHEN_TRAFFIC_DONE:
                    if not traffic_generator_process.is_alive():
                        raise KeyboardInterrupt()

            if show_cpu:
                app_cpu = app_ps.cpu_percent()
                app_mem = app_ps.memory_info()
                broker_cpu = broker_ps.cpu_percent()
                broker_mem = broker_ps.memory_info()
                if app_cpu > 0.0:
                    total_app_cpu += app_cpu
                    total_broker_cpu += broker_cpu
                    count += 1
                    # print(f"app cpu={app_cpu}, app avg cpu={total_app_cpu/count}, app mem={app_mem.rss}, broker cpu={broker_cpu},"
                    #     f" broker avg cpu={total_broker_cpu/count}, broker_mem={broker_mem.rss}")
                    db_access.write(
                        db_access.prepare(
                            {
                                "time": dt.datetime.utcnow(),
                                "app_cpu": app_cpu,
                                "app_mem": app_mem.rss,
                                "broker_cpu": broker_cpu,
                                "broker_mem": broker_mem.rss,
                            }
                        )
                    )

                time.sleep(1)

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


def run(app_name, config, env_name):
    config_file = config
    dtl_app = getattr(sim, app_name, None)
    if dtl_app is None:
        dtl_app = getattr(simplex, app_name, sim.ofdm_adaptive_sim_src)

    # Load flow config
    cfg = {}
    with open(config_file, "r") as f:
        content = f.read()
        cfg = json.loads(content)
        env_cfg = env.load_config(env_name)
        env_cfg["logs"] = env.log_path(env_name)

        run_app(dtl_app, cfg, env_name, env_cfg, config_file)