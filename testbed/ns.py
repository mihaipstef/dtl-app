import ipcalc
import iptc
from pyroute2 import (
    IPRoute,
    NetNS,
    netns,
)
import os
from testbed import (
    arp,
)

LOCAL_ROUTING_TABLE = 255
DEFAULT_ROUTING_TABLE = 254
INCOMING_LOCAL_TRAFFIC_TABLE = 19
DTL_BR_NAME = "dtl-br"
DTL_BR_SUBNET = "192.168.0.0/24"
DTL_BR_GW = str(ipcalc.Network("192.168.0.0/24") + 1)


def _create_tuntap(ns, mode, if_name, addresses, mask):
    ip_addr, *mac_addr = addresses
    mac_addr = mac_addr[0] if mac_addr else None
    links = ns.link_lookup(ifname=if_name)
    if len(links) > 0:
        # Link already exists
        return
    else:
        ns.link("add", ifname=if_name, kind="tuntap", mode=mode)
        tun_idx = ns.link_lookup(ifname=if_name)[0]
        if mac_addr:
            ns.link("set", index=tun_idx, address=mac_addr)
        tun_addr = ns.get_addr(index=tun_idx)
        assert (len(tun_addr) <= 1)
        if len(tun_addr) == 0:
            ns.addr("add", index=tun_idx, address=ip_addr, mask=mask)
        ns.link("set", index=tun_idx, mtu=200, txqlen=1000)
        ns.link("set", index=tun_idx, state="up")


def _create_tun(ns, if_name, addresses, mask):
    return _create_tuntap(ns, "tun", if_name, addresses, mask)


def _create_tap(ns, if_name, addresses, mask):
    return _create_tuntap(ns, "tap", if_name, addresses, mask)


def _get_attribute(attrs, k):
    return {k: v for (k, v) in attrs}.get(k, None)


def _setup_local_route(ns, if_name):
    idx = ns.link_lookup(ifname=if_name)[0]
    if_addr = _get_attribute(ns.get_addr(index=idx)[0]["attrs"], "IFA_ADDRESS")
    rules = ns.get_rules(
        match=lambda x: x["table"] == INCOMING_LOCAL_TRAFFIC_TABLE and if_name == _get_attribute(
            x["attrs"], "FRA_IIFNAME"))
    if len(rules) == 0:
        ns.route("add", dst=f"{if_addr}", type="local", scope="host", oif=idx, table=INCOMING_LOCAL_TRAFFIC_TABLE)
        ns.rule("add", iifname=if_name, table=INCOMING_LOCAL_TRAFFIC_TABLE)


def  _setup_one_way_route(ns, oif_name, dst_ip_addr):
    oidx = ns.link_lookup(ifname=oif_name)[0]
    routes_to_dst = ns.get_routes(
        match=lambda x: x["table"] == DEFAULT_ROUTING_TABLE and dst_ip_addr == _get_attribute(
            x["attrs"], "RTA_DST"))
    if len(routes_to_dst) == 0:
        ns.route("add", dst=f"{dst_ip_addr}", scope="link", oif=oidx, table=DEFAULT_ROUTING_TABLE)


def _setup_p2p_routes(ns, if1_name, if2_name):
    if1_addr = _get_attribute(ns.get_addr(label=if1_name)[0]["attrs"], "IFA_ADDRESS")
    if2_addr = _get_attribute(ns.get_addr(label=if2_name)[0]["attrs"], "IFA_ADDRESS")
    _setup_one_way_route(ns, if1_name, if2_addr)
    _setup_one_way_route(ns, if2_name, if1_addr)


def _find_gw_route(ip):
    routes = ip.get_routes(match=lambda x: x["table"] == DEFAULT_ROUTING_TABLE and None != _get_attribute(x["attrs"], "RTA_GATEWAY"))
    if len(routes) > 0:
        gw_idx = _get_attribute(routes[0]["attrs"], "RTA_OIF")
        gw_iname = _get_attribute(ip.get_links(gw_idx)[0]["attrs"], "IFLA_IFNAME")
        return gw_iname
    return None


def _setup_bridge(ip):
    # look for bridge
    links = ip.link_lookup(ifname=DTL_BR_NAME)
    if len(links) == 0:
        ip.link("add", ifname=DTL_BR_NAME, kind="bridge")
        br_idx = ip.link_lookup(ifname="dtl-br")[0]
        ip.addr("add", index=br_idx, address=DTL_BR_GW)
        ip.link("set", index=br_idx, state="up")
        nat_chain = iptc.Chain(iptc.Table(iptc.Table.NAT), "POSTROUTING")
        for r in nat_chain.rules:
            if DTL_BR_SUBNET.split('/')[0] == r.src.split('/')[0]:
                nat_chain.delete_rule(r)
        rule = iptc.Rule(chain=nat_chain)
        rule.target = iptc.Target(rule, "MASQUERADE")
        rule.src = DTL_BR_SUBNET
        rule.out_interface = f"!{DTL_BR_NAME}"
        nat_chain.insert_rule(rule)
        return br_idx
    return links[0]


def _get_available_address(ip):
    def __is_weth(x):
        return x is not None and x.endswith("-weth")
    used_addresses = []
    for ns_name in netns.listnetns():
        ns = NetNS(ns_name, flags=os.O_RDONLY)
        used_addresses += [ _get_attribute(a["attrs"], "IFA_ADDRESS")
            for a in ns.get_addr(match=lambda x: __is_weth(_get_attribute(x["attrs"], "IFA_LABEL")))]
    used_addresses = set(used_addresses)
    available_addr = ipcalc.IP(DTL_BR_GW) + 1
    for _ in range(253):
        if (a:=str(available_addr)) not in used_addresses:
            return a
        available_addr = available_addr + 1
    return None


def _setup_world_connection(ns):
    ip = IPRoute()
    if (addr:=_get_available_address(ip)) is not None:
        br_idx = _setup_bridge(ip)

        weth_name = f"{ns.netns}-weth"
        wbr_name = f"{ns.netns}-wpeer"

        ip.link("add", ifname=wbr_name, kind="veth", peer={"ifname": weth_name, "net_ns_fd": ns.netns})

        weth_idx = ns.link_lookup(ifname=weth_name)[0]
        ns.link("set", index=weth_idx)
        ns.addr("add", index=weth_idx, address=addr, mask=24)
        ns.link("set", index=weth_idx, state="up")

        wbr_idx = ip.link_lookup(ifname=wbr_name)[0]
        ip.link("set", index=wbr_idx, master=br_idx)
        ip.link("set", index=wbr_idx, state="up")

        ns.route("add", gateway=DTL_BR_GW)


def _get_mac_addr(ns, ifname):
    links = ns.get_links(ifname=ifname)
    if len(links) > 0:
        mac = _get_attribute(links[0]["attrs"], "IFLA_ADDRESS")
        return mac
    return None


def get_mac_addr(ifname):
    return _get_mac_addr(IPRoute(), ifname)


def get_tuntap_type(ifname):
    links = IPRoute().get_links(ifname=ifname)
    if len(links) > 0:
        try:
            link_attrs = links[0].get_attr("IFLA_LINKINFO")
            iface_kind = _get_attribute(link_attrs["attrs"], "IFLA_INFO_KIND")
            if iface_kind == "tun":
                iface_type = _get_attribute(
                    _get_attribute(link_attrs["attrs"], "IFLA_INFO_DATA")["attrs"],
                    "IFLA_TUN_TYPE"
                )
            return iface_type
        except Exception:
            return None
    return None


def create_tun_env(env_name, env_config=None, overwrite=False):
    ip_addrs = [t[0] for t in env_config.get("tunnel", [])]
    mac_addrs = [t[1] if len(t)>=2 else None for t in env_config.get("tunnel", [])]
    env_type = env_config.get("type", "sim")
    if len(ip_addrs) < 2:
        raise Exception(f"Environment requires 2 IP addresses. Check config.")
    if overwrite:
        ns = NetNS(env_name, flags=os.O_CREAT | os.O_RDWR | os.O_TRUNC)
    else:
        ns = NetNS(env_name, flags=os.O_CREAT)
    # create tun0 interface
    _create_tun(ns, "tun0", (ip_addrs[0], mac_addrs[0]), 32)
    # create tun1 interface (only for sim environment)
    if env_type == "sim":
        _create_tun(ns, "tun1", (ip_addrs[1], mac_addrs[1]), 32)
    # delete local routes created by default
    ns.flush_routes(table=LOCAL_ROUTING_TABLE)
    # setup routes for accepting local incoming traffic
    _setup_local_route(ns, "tun0")
    if env_type == "sim":
        _setup_local_route(ns, "tun1")
        # setup p2p routes
        _setup_p2p_routes(ns, "tun0", "tun1")
    else:
        _setup_one_way_route(ns, "tun0", ip_addrs[1])
    # Up loopback interface
    ns.link("set", index=ns.link_lookup(ifname="lo")[0], state="up")
    # Connect the env to the Internet
    _setup_world_connection(ns)
    return ns


def create_tap_env(env_name, env_config=None, overwrite=False):
    ip_addrs = [t[0] for t in env_config.get("tunnel", [])]
    mac_addrs = [t[1] if len(t)>=2 else None for t in env_config.get("tunnel", [])]
    env_type = env_config.get("type", "sim")
    if len(ip_addrs) < 2:
        raise Exception(f"Environment requires 2 IP addresses. Check config.")
    if overwrite:
        ns = NetNS(env_name, flags=os.O_CREAT | os.O_RDWR | os.O_TRUNC)
    else:
        ns = NetNS(env_name, flags=os.O_CREAT)
    # create tap0 interface
    _create_tap(ns, "tap0", (ip_addrs[0], mac_addrs[0]), 32)
    # create tap1 interface (only for sim env)
    if env_type == "sim":
        _create_tap(ns, "tap1", (ip_addrs[1], mac_addrs[1]), 32)
    # delete local routes created by default
    ns.flush_routes(table=LOCAL_ROUTING_TABLE)
    # setup routes for accepting local incoming traffic
    _setup_local_route(ns, "tap0")
    if env_type == "sim":
        _setup_local_route(ns, "tap1")
        # setup p2p routes
        _setup_p2p_routes(ns, "tap0", "tap1")
    else:
        _setup_one_way_route(ns, "tap0", ip_addrs[1])
    # Up loopback interface
    ns.link("set", index=ns.link_lookup(ifname="lo")[0], state="up")
    # Connect the env to the Internet
    _setup_world_connection(ns)
    # Set ARP static entries for tap interfaces
    arp.set_arp_entry(env_name, ip_addrs[0], _get_mac_addr(ns, "tap0"))
    arp.set_arp_entry(env_name, ip_addrs[1], _get_mac_addr(ns, "tap1"))
    return ns


def set_env_for_proccess(env_name):
    netns.setns(env_name, flags=os.O_RDONLY)


def delete_env(name):
    netns.remove(netns=name)
