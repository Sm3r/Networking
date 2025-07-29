#!/usr/bin/env python3

import sys
import os
import random
import time
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from topology import CustomTopology

# def generate_traffic(net, duration=60):
#     # TODO: Select automatically which hosts to use as servers and clients
#     h1 = net.get('h1')
#     h2 = net.get('h2')
#     end_time = time.time() + duration
#
#     traffic_types = ['http', 'ftp', 'netcat']
#
#     while time.time() < end_time:
#         choice = random.choice(traffic_types)
#         if choice == 'http':
#             h2.cmd('python3 -m http.server 8080 &')
#             time.sleep(1)
#             h1.cmd('curl http://10.0.0.2:8080/index.html')
#
#         elif choice == 'ftp':
#             h1.cmd('ftp 10.0.0.2')  # Make sure FTP is set up
#
#         elif choice == 'netcat':
#             h2.cmd('nc -l -p 5001 > /dev/null &')
#             h1.cmd('cat /dev/urandom | head -c 1M | nc 10.0.0.2 5001')
#
#         time.sleep(random.randint(2, 5))

def setup(dot_file_path):
    topo = CustomTopology(dot_file_path)
    controller = RemoteController('ryuController', ip='127.0.0.1', port=6653)

    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=controller,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink
    )
    nat = net.addNAT().configDefault()

    # BUG: DNS not working

    # info(f"*** Setting up DNS...\n")
    # for host in net.hosts:
    #     if host.name.startswith('h'):
    #         info(f"{host.name} ")
    #         interfaces = host.cmd("ls /sys/class/net") 
    #         for intf in interfaces.split(' '):
    #             if host.name not in intf:
    #                 continue
    #             host.cmd(f"resolvectl dns {intf} 8.8.8.8")
    #         host.cmd(f"systemctl restart systemd-resolved")
    # info("\n")


    # info(f"*** Setting up DNS...\n")
    # for host in net.hosts:
    #     if host.name.startswith('h'):
    #         info(f"{host.name} ")
    #         host.cmd('ip route add default via 10.0.0.254')
    #         host.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    # info("\n")
    return net, nat

def run(dot_file_path):
    net, nat = setup(dot_file_path)

    info("*** Starting network...\n")
    net.start()

    time.sleep(1)

    info("*** Running ping test...\n")
    net.pingAll()

    hostCount = len(net.hosts)
    hostname = net.hosts[random.randint(0, hostCount - 1)]
    info(f"*** Testing external internet access from host {hostname}...\n")
    hostname.cmdPrint('ping -c 2 8.8.8.8')

    # generate_traffic(net, duration=5)
    CLI(net)

    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    if len(sys.argv) != 2:
        print(f"Usage: sudo python3 {sys.argv[0]} <topology.dot>")
    else:
        run(sys.argv[1])
