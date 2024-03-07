from scapy.config import conf


def scapy_reload(f):
    def wrap(*args, **kwargs):
        conf.ifaces.reload()
        conf.route.resync()
        conf.use_pcap = False
        f(*args, **kwargs)
    return wrap

