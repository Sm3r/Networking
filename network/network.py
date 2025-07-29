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

    info("*** Configuring DNS for hosts...\n")
    for host in net.hosts:
        resolv_file_path = f'/tmp/{host.name}.resolv.conf'
        with open(resolv_file_path, 'w') as f:
            f.write('nameserver 8.8.8.8\n') # Google DNS
            f.write('nameserver 1.1.1.1\n') # Cloudflare DNS

        host.cmd(f'mount --bind {resolv_file_path} /etc/resolv.conf')
        info(f" {host.name}")
    info("\n")

    return net, nat

def run(dot_file_path):
    net, nat = setup(dot_file_path)

    info("*** Starting network...\n")
    net.start()

    # It's good practice to wait a moment for the controller and switches to connect.
    time.sleep(2)

    info("*** Running initial connectivity test (pingAll)...\n")
    net.pingAll()

    # random_host = random.choice(net.hosts)
    for host in net.hosts:
        info(f"*** Testing external internet access from host {host.name}...\n") 
        info(f"--> Pinging IP (8.8.8.8):\n")
        host.cmdPrint('ping -c 2 8.8.8.8') 

    for host in net.hosts:
        info(f"*** Testing DNS name resolution from host {host.name}...\n") 
        info(f"--> Pinging Hostname (google.com):\n")
        host.cmdPrint('ping -c 2 google.com')

    # generate_traffic(net, duration=5)
    CLI(net)

    info("*** Stopping network...\n")
    net.stop()

if __name__ == '__main__':
    # Check for the topology file argument
    if len(sys.argv) != 2:
        print(f"Usage: sudo python3 {sys.argv[0]} <topology.dot>")
        sys.exit(1)

    # Ensure the topology file exists
    topology_file = sys.argv[1]
    if not os.path.isfile(topology_file):
        print(f"Error: Topology file not found at '{topology_file}'")
        sys.exit(1)
        
    setLogLevel('info')
    run(topology_file)
