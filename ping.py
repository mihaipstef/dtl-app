#!/usr/bin/env python3

import argparse
import datetime as dt
import multiprocessing as mp
import pymongo
from scapy.layers.inet import (
    ICMP,
    IP,
)
from scapy.sendrecv import (
    sr1,
)

def _ping(ip_addr, col):
    sent = 0
    rcv = 0
    seq = 0
    while True:
        packet = IP(dst=ip_addr, ttl=64) / ICMP(seq=seq, id=100) / "".join(["a" for _ in range(64)])
        seq += 1
        ans = sr1(packet, timeout=3, inter=1, verbose=0)
        sent += 1
        t = None
        if ans:
            t = ans.time - packet.sent_time
            col.insert_one({"probe_name": "icmp_ping_time", "insert_ts": dt.datetime.utcnow(), "time": t * 1000})
            rcv += 1
        print(f"sent={sent}, received={rcv}, time={t}s")
        col.insert_one({"probe_name": "icmp_ping_failure", "insert_ts": dt.datetime.utcnow(), "fail_rate": 100 * (sent - rcv)/sent})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--addr", type=str, default="3.3.3.3", help="IP address to ping")
    parser.add_argument("--db", type=str, default="mongodb://probe:probe@127.0.0.1:27017", help="URI of the database that stores probe data")
    parser.add_argument("--collection", type=str, default="test", help="Collection to use")

    args = parser.parse_args()

    db_client = pymongo.MongoClient(args.db)
    db = db_client["probe_data"]
    col = db[args.collection]

    ping_proc = mp.Process(target=_ping, args=(args.addr, col,))
    ping_proc.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        if ping_proc and ping_proc.is_alive():
            ping_proc.terminate()


