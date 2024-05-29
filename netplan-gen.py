import argparse
from argparse import RawTextHelpFormatter
import sys
import socket

desc="""This script generates dumb netplan configurations.

For a given server rank, and a list of interfaces, it will bind
10.10.RANK.i to each interface i. For instance, on server rank 1:
    ens5f0 <- 10.10.1.0
    ens5f1 <- 10.10.1.1
    ens5f2 <- 10.10.1.2

The expected usage is to write the output to yaml file and update netplan. E.g:

  $ python3 netplan-gen.py --rank 1 -iprefix ens > my_iface_config.yaml
  $ sudo cp my_iface_config.yaml /etc/netplan/
  $ sudo netplan apply
"""

parser = argparse.ArgumentParser(description=desc, formatter_class=RawTextHelpFormatter)

parser.add_argument("-r", "--rank", required=True, type=int, choices=range(0,256), metavar="[0-255]", help="The node's rank")
parser.add_argument("-j", "--jumbo-frames", required=False, help="Enable jumbo frames for all interfaces", action="store_true")
ifgroup = parser.add_mutually_exclusive_group(required=True)
ifgroup.add_argument("-i", action='store', type=str, nargs='+', help="Configure the specified list of interfaces")
ifgroup.add_argument("-iprefix", action='store', type=str, help="Configure all interfaces starting with given prefix")

def generate_netplan(rank, ifaces):
    if len(ifaces) == 0:
        print("error: did not find any interfaces")
        sys.exit(1)

    res = "network:\n"
    res += "  version: 2\n"
    res += "  renderer: networkd\n"
    res += "  ethernets:\n"

    for i, iface in enumerate(sorted(ifaces)):
        res += "    %s:\n" % iface
        res += "      dhcp4: no\n"
        res += "      addresses:\n"
        res += "        - 10.10.%d.%d\n" % (rank, i)
    print(res)

def get_ifs(ifs):
    res = set()
    available_ifs = [iface for _, iface in socket.if_nameindex()]
    for iface in ifs:
        if iface in available_ifs:
            res.add(iface)
        else:
            print("warning: interface '%s' not found, skipping..." % iface)
    return list(res)

def get_ifs_with_prefix(prefix):
    if len(prefix) == 0:
        print("error: prefix cannot be empty")
        sys.exit(1)
    res = set()
    for _, iface in socket.if_nameindex():
        if iface.startswith(prefix):
            res.add(iface)
    return list(res)

if __name__ == "__main__":
    opts = parser.parse_args()
    ifs = get_ifs(opts.i) if opts.i is not None else get_ifs_with_prefix(opts.iprefix)
    generate_netplan(opts.rank, ifs)
