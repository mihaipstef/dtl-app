#!/usr/bin/env python3

import argparse
import testbed.traffic.icmp_gen as gen
import multiprocessing as mp
from scapy.all import (
    get_if_addr,
)
from time import sleep

parser = argparse.ArgumentParser()

parser.add_argument("--src_iface", type=str, default="tun0",
                    help="Source interface")
parser.add_argument("--dst_iface", type=str, default="tun1",
                    help="Destination interface")
parser.add_argument("--size", type=str, default="64",
                    help="Payload size")
parser.add_argument("--rate", type=str, default="1",
                    help="Packet generation rate (packets/sec)")

args = parser.parse_args()

src_ip = get_if_addr(args.src_iface)
dst_ip = get_if_addr(args.dst_iface)

sniff_process = mp.Process(
    target=gen.icmp_sniff, args=(None, src_ip, args.dst_iface, True,))
sniff_process.start()
sleep(1)
gen_process = mp.Process(
    target=gen.icmp_gen, args=(None, dst_ip, int(args.size),float(args.rate),))
gen_process.start()

try:
    while True:
        pass
except KeyboardInterrupt as _:
    if gen_process and gen_process.is_alive():
        gen_process.terminate()
    if sniff_process and sniff_process.is_alive():
        gen_process.terminate()
    sleep(1)