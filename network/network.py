
import os
import sys
import time
from typing import Tuple

import numpy as np
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.nodelib import NAT

from capture.packetsniffer import PacketSniffer
from logger import setup_logger
from simulation.simulation import Simulation
from topology import CustomTopology

logger = setup_logger()

#  Setup the DNS for each host of the network
def setup_dns(net: Mininet):

    logger.info('Configuring DNS for hosts...\n')
    logger.debug('  ┗  ', extra={'no_header': True})
    for host in net.hosts:
        resolv_file_path = f'/tmp/{host.name}.resolv.conf'
        with open(resolv_file_path, 'w') as f:
            f.write('nameserver 8.8.8.8\n') # Google DNS
            f.write('nameserver 1.1.1.1\n') # Cloudflare DNS

        host.cmd(f'mount --bind {resolv_file_path} /etc/resolv.conf')
        logger.debug(f'{host.name} ', extra={'no_header': True})
    logger.debug('\n', extra={'no_header': True})

# Setup and start an FTP server for each marked host
def setup_ftp_servers(net: Mininet):

    logger.info(f'Configuring FTP servers...\n')
    logger.debug('  ┗  ', extra={'no_header': True})
    for server_name in net.topo.servers:
        server_host = net.get(server_name)
        
        # Create a unique file for this server
        file_to_download = f'file_from_{server_name}.txt'
        server_host.cmd(f'echo "Data from {server_name}" > /srv/ftp/{file_to_download}')
        server_host.cmd(f'chmod 644 /srv/ftp/{file_to_download}')

        # Configure vsftpd to enable anonymous donwloads
        server_host.cmd(f'sudo sed -i "s/^#* *anonymous_enable=NO/anonymous_enable=YES/" /etc/vsftpd.conf')
        
        # Start FTP server
        server_host.cmd('/usr/sbin/vsftpd &')

        logger.debug(f'{server_name} ', extra={'no_header': True})
    logger.debug('\n', extra={'no_header': True})

    # Check if FTP servers are working
    for server_name in net.topo.servers:
        result = server_host.cmd('pgrep vsftpd')
        if result.strip() == '':
            logger.error(f'{server_name} FTP server is not running\n')

# Generate and configure a Mininet network describing the topology from a Graphviz dot file
def setup(dot_file_path: str) -> Tuple[Mininet, NAT]:
    
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

    setup_dns(net)
    setup_ftp_servers(net)
    return net, nat

# Configure and start the simulation
def start_simulation(net: Mininet):

    DAYS            = 1                            # simulate a week of traffic
    PACKETS_PER_MIN = 2          # average across the traffic signal curve
    total_duration  = DAYS * 24 * 60 * 60                     # virtual seconds
    total_requests  = PACKETS_PER_MIN * DAYS * 24 * 60       # ~30240

    sim = Simulation(
        net=net,
        traffic_distribution_csv_path='resources/traffic_signal.csv',
        website_list_path='resources/website-list.json',
        file_list_path='resources/file-list.json',
        start_time_of_day=np.random.randint(0, 86400),
        total_requests_count=total_requests,
        total_duration=total_duration,
        is_real_time=False,   # advance virtual time as fast as the network allows
        time_step=60          # 1-min buckets are enough for a multi-day span
    )
    capture = PacketSniffer(simulation=sim, interface='any')

    # Starting network capture and simulation
    try:
        capture.start_capture(output_filename='simple')
    except Exception as e:
        return

    time.sleep(2)
    sim.start()

    logger.info(f"{sim._format_time_pretty(sim.get_time())} Wait for simulation thread to fully terminate...\n")
    time.sleep(5)
    sim.wait_for_completion(timeout=None)   # wait as long as needed
    time.sleep(5)
    capture.stop_capture()
    logger.info(f"{sim._format_time_pretty(sim.get_time())} Simulation terminated!\n")

# Destroy Mininet network
def teardown(net: Mininet):

    logger.debug('Stopping FTP servers...\n')
    logger.debug('  ┗  ', extra={'no_header': True})
    for server_name in net.topo.servers:
        net.get(server_name).cmd('pkill vsftpd')
        logger.debug(f'{server_name} ', extra={'no_header': True})
    logger.debug('\n', extra={'no_header': True})

    logger.info('Stopping network...\n')
    net.stop()

# Start the Mininet network and the traffic generation
def run(dot_file_path: str):

    net, nat = setup(dot_file_path)

    logger.info('Starting network...\n')
    net.start()
    net.topo.set_latency(net)
    time.sleep(2)
    
    logger.info(f'Network started!\n')
    start_simulation(net)

    # CLI(net) 

    teardown(net)

if __name__ == '__main__':
    # Check for the topology file argument
    if len(sys.argv) != 2:
        print(f"Usage: sudo python3 {sys.argv[0]} [topology.dot]")
        sys.exit(1)

    # Ensure the topology file exists
    topology_file = sys.argv[1]
    if not os.path.isfile(topology_file):
        print(f"Error: Topology file not found at '{topology_file}'")
        sys.exit(1)
    
    # log.setLogLevel('info')
    run(topology_file)
