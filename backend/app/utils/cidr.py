import ipaddress
from typing import Iterable, List


def expand_cidr(cidr: str) -> List[str]:
    """展开单个 CIDR 为主机列表"""
    network = ipaddress.ip_network(cidr, strict=False)
    return [str(host) for host in network.hosts()]


def expand_cidrs(cidrs: List[str]) -> List[str]:
    """展开多个 CIDR 为主机列表"""
    hosts: List[str] = []
    for cidr in cidrs:
        network = ipaddress.ip_network(cidr, strict=False)
        for host in network.hosts():
            hosts.append(str(host))
    return hosts


