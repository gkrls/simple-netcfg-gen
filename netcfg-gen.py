import argparse
from argparse import RawTextHelpFormatter
import sys
import socket

desc = """This script generates dumb net configurations.

For a given server rank, and a list of interfaces, it will bind address
10.10.INTERFACE.RANK to each interface i. For instance, on server rank 1:
    ens5f0 <- 10.0.0.1
    ens5f1 <- 10.0.1.1
    ens5f2 <- 10.0.2.1
"""

parser = argparse.ArgumentParser(
    description=desc, formatter_class=RawTextHelpFormatter)

parser.add_argument("-m", "--mode", required=True, type=str, choices=['netplan', 'sh', 'config'],
                    help="Type of config file to generate. Options:\n"
                         "  netplan - Netplan yaml output\n"
                         "       sh - Shell script\n"
                         "   config - Config file to be copied under /etc/network/interfaces.d")
parser.add_argument("-r", "--rank", required=True, type=int,
                    choices=range(0, 256), metavar="[0-255]", help="The node's rank")
parser.add_argument("-j", "--jumbo-frames", required=False,
                    help="Enable jumbo frames for all interfaces", action="store_true")
ifgroup = parser.add_mutually_exclusive_group(required=True)
ifgroup.add_argument("-i", action='store', type=str, nargs='+',
                     help="Configure the specified list of interfaces")
ifgroup.add_argument("-iprefix", action='store', type=str,
                     help="Configure all interfaces starting with given prefix")


def generate_netplan(rank, jumbo_frames, ifaces):
    res = "network:\n"
    res += "  version: 2\n"
    res += "  renderer: networkd\n"
    res += "  ethernets:\n"
    for i, iface in enumerate(sorted(ifaces)):
        res += "    %s:\n" % iface
        res += "      dhcp4: no\n"
        res += "      addresses:\n"
        res += "        - 10.0.%d.%d/24\n" % (i, rank)
        if jumbo_frames:
            res += "      mtu: 9000\n"
    return res


def generate_sh(rank, jumbo_frames, ifaces):
    res = ""
    for i, iface in enumerate(sorted(ifaces)):
        res += "sudo ip addr add 10.0.%d.%d/24 dev %s\n" % (i, rank, iface)
        res += "sudo ip link set %s up\n" % iface
    return res


def generate_config(rank, jumbo_frames, ifaces):
    res = ""
    for i, iface in enumerate(sorted(ifaces)):
        res += "auto %s\n" % iface
        res += "iface %s inet static\n" % iface
        res += "    address 10.0.%d.%d\n" % (i, rank)
        res += "    netmask 255.255.255.0\n"
    return res


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
    ifs = get_ifs(opts.i) if opts.i is not None else get_ifs_with_prefix(
        opts.iprefix)
    if len(ifs) == 0:
        print("error: did not find any interfaces")
        sys.exit(1)

    if opts.mode == 'netplan':
        print(generate_netplan(opts.rank, opts.jumbo_frames, ifs))
    elif opts.mode == 'config':
        print(generate_config(opts.rank, opts.jumbo_frames, ifs))
    else:
        print(generate_sh(opts.rank, opts.jumbo_frames, ifs))
