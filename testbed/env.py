import json
import os
from pathlib import Path
import shutil
from testbed import (ns, run as run_app)


DTL_ENV_FOLDER = ".dtl_envs"


def _env_path(env_name):
    relative_env_path = f"{DTL_ENV_FOLDER}/{env_name}"
    if (sudo_user:=os.getenv("SUDO_USER", None)):
        home_path = os.path.expanduser(f"~{sudo_user}")
        return f"{home_path}/{relative_env_path}"
    return f"{Path.home()}/{relative_env_path}"


def _create_env_folder(env_name, env_config):
    env_path = _env_path(env_name)
    base_path = os.path.dirname(env_path)
    if not os.path.isdir(base_path):
        os.mkdir(base_path)
    os.mkdir(env_path)
    shutil.copyfile(env_config, f"{env_path}/config.json")
    os.mkdir(f"{env_path}/logs")


def _recursive_chown_if_sudo(name):
    if (sudo_user:=os.getenv("SUDO_USER", None)):
        env_path = _env_path(name)
        for dirpath, dirnames, filenames in os.walk(env_path):
            shutil.chown(dirpath, sudo_user, sudo_user)
            for filename in filenames:
                shutil.chown(os.path.join(dirpath, filename), sudo_user, sudo_user)


_env_create = {
    "sim": {
        "tap": ns.create_sim_tap_env,
        "tun": ns.create_sim_tun_env,
    }
}

def load_config(env_name):
    config_file = f"{_env_path(env_name)}/config.json"
    with open(config_file, "r") as f:
        content = f.read()
        cfg = json.loads(content)
        return cfg


def log_path(env_name):
    return f"{_env_path(env_name)}/logs"


def create(name, config):
    env_path = _env_path(name)
    if os.path.isdir(env_path):
        raise Exception(f"Environment {name} already exists. Use start command to activate it.")
    else:
        try:
            _create_env_folder(name, config)
            with open(f"{env_path}/config.json", "r") as f:
                config_json = json.load(f)
                try:
                    _env_create[config_json["type"]][config_json["mode"]](name, config_json)
                except:
                    raise Exception("Something is wrong with env config!")
        finally:
            _recursive_chown_if_sudo(name)


def start(name):
    env_path = _env_path(name)
    if not os.path.isdir(env_path):
        raise Exception(f"Environment {name} doesn't exist.")
    else:
        with open(f"{env_path}/config.json", "r") as f:
            config = json.load(f)
            try:
                _env_create[config["type"]][config["mode"]](name, config)
            finally:
                _recursive_chown_if_sudo(name)


def stop(name):
    ns.delete_env(name)


def delete(name):
    env_path = _env_path(name)
    if not os.path.isdir(env_path):
        raise Exception(f"Environment {name} doesn't exist.")
    else:
        stop(name)
        shutil.rmtree(env_path)


def run(name, app, config):
    ns.set_env_for_proccess(name)
    try:
        run_app.run(app, config, name)
    finally:
        _recursive_chown_if_sudo(name)

