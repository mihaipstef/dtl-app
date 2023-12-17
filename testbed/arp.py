from pyroute2 import (
    NSPopen,
)
import os
import subprocess


def set_arp_entry(env_name, ip_addr, mac_addr):
    print( ["arp", "-s", ip_addr, mac_addr])
    nsp = NSPopen(env_name, ["arp", "-s", ip_addr, mac_addr], stdout=subprocess.PIPE)
    #nsp = NSPopen(env_name, ["ip", "ad"], stdout=subprocess.PIPE)
    #print(nsp.communicate())
    nsp.wait()
    nsp.release()


def get_arp_entry(ip_addr, ifname):
    p = subprocess.Popen(["arp", "-ai", ifname], stdout=subprocess.PIPE)
    #nsp = NSPopen(env_name, ["ip", "ad"], stdout=subprocess.PIPE)
    output = p.communicate()
    #print(output)
    p.wait()
    p.terminate()
    for line in output[0].decode().split("\n"):
        if line:
            _, ip, _, mac_addr, _ = line.split(maxsplit=4)
            if ip.strip("()") == ip_addr:
                return mac_addr
    return None