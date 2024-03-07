#!/usr/bin/env python3

import argparse
from testbed.traffic.icmp_gen import icmp_ping
import multiprocessing as mp
import pymongo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--addr", type=str, default="3.3.3.3", help="IP address to ping")
    parser.add_argument("--db", type=str, default="mongodb://probe:probe@127.0.0.1:27017", help="URI of the database that stores probe data")
    parser.add_argument("--collection", type=str, default="test", help="Collection to use")

    args = parser.parse_args()

    db_client = pymongo.MongoClient(args.db)
    db = db_client["probe_data"]
    col = db[args.collection]

    ping_proc = mp.Process(target=icmp_ping, args=(col, args.addr,), kwargs={"verbose": True})
    ping_proc.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        if ping_proc and ping_proc.is_alive():
            ping_proc.terminate()


