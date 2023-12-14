import influxdb
import pymongo
from typing import Protocol
from urllib.parse import urlparse


class db_access(Protocol):
    def write(self, data):...
    def write_batch(self, data):...
    def prepare(self, data):...
    def query(self, q, **kwargs):...


class mongo_access(db_access):

    def __init__(self, uri, name, overwrite = True):
        self.client = pymongo.MongoClient(uri)
        self.collection = self.client["monitor"][name]
        if overwrite:
            self.collection.drop()
            self.collection = self.client["monitor"][name]
        self.collection.create_index([ ("time", -1) ])

    def write(self, data):
        self.collection.insert_one(data)

    def write_batch(self, data):
        if len(data):
            self.collection.insert_many(data)

    def prepare(self, data):
        return data

    def query(self, q, **kwargs):
        func_name = kwargs.get("func", "find")
        f = getattr(self.collection, func_name, None)
        if f is not None and callable(f):
            return f(q)
        return None

class influx_access(db_access):

    def __init__(self, url, username, password, name):
        if "//" not in url:
            url = f"http://{url}"
        parsed_url = urlparse(url)
        self.client = influxdb.InfluxDBClient(
            host=parsed_url.hostname,
            port=parsed_url.port,
            username=username,
            password=password,
            database=name)
        self.db_name = name
        self.client.create_database(name)

    def write(self, data):
        self.client.write_points([data], time_precision='ms')

    def write_batch(self, data):
        self.client.write_points(data, time_precision='ms')

    def prepare(self, data):
        influx_data = {
            "measurement": data.get("probe_name", "john_doe"),
            "time": data.get("time", None),
            "fields": {
                k: data[k] for k in data if k not in ["time", "probe_name"]
            }
        }
        return influx_data

    def query(self, q, **kwargs):
        raise Exception("Not implemented")


def db(name, **kwargs) -> db_access:
    db_type = kwargs.get("db_type", None)
    overwrite = kwargs.get("overwrite", True)
    if db_type == "mongo":
        return mongo_access(**kwargs["access"], name=name, overwrite=overwrite)
    elif db_type == "influx":
        return influx_access(kwargs["url"], kwargs["username"], kwargs["password"], name=name)
    raise Exception("Unknown database")
