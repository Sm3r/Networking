#!/usr/bin/env python3

import sys
import os
import random
import time
import logging
from mininet import log
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.nodelib import NAT
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from topology import CustomTopology
from customlogger.colors import LoggerColors
from customlogger.formatter import CustomFormatter
from typing import Tuple
from simulation.taskqueue import TaskQueue
from simulation.task import Task
from simulation.simulation import Simulation
from capture.packetsniffer import PacketSniffer

logger = logging.getLogger('networking')

def setup_dns(net: Mininet):
    """
    Setup the DNS for each host of the network

    Attributes:
        net (Mininet): a Mininet network
    """
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

def setup_ftp_servers(net: Mininet):
    """
    Setup and start an FTP server for each marked host

    Attributes:
        net (Mininet): a Mininet network
    """
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

def setup(dot_file_path: str) -> Tuple[Mininet, NAT]:
    """
    Generate and configure a Mininet network describing the topology from a Graphviz dot file

    Attributes:
        dot_file_path (str): path of the dot file
    """
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

def teardown(net: Mininet):
    """
    Destroy a Mininet network

    Attributes:
        net (Mininet): a Mininet network
    """
    logger.debug('Stopping FTP servers...\n')
    logger.debug('  ┗  ', extra={'no_header': True})
    for server_name in net.topo.servers:
        net.get(server_name).cmd('pkill vsftpd')
        logger.debug(f'{server_name} ', extra={'no_header': True})
    logger.debug('\n', extra={'no_header': True})

    logger.info('Stopping network...\n')
    net.stop()

def start_simulation(net: Mininet):
    """
    Configure and start the simulation

    Attributes:
        net (Mininet): a Mininet network
    """
    sim = Simulation(
        net=net,
        website_list_path='resources/website-list.json',
        file_list_path='resources/file-list.json',
        mean_requests_count=15,
        total_duration=2.0
    )
    capture = PacketSniffer(simulation=sim)

    # Starting network capture and simulation
    try:
        capture.start_capture(output_filename='test')
    except Exception as e:
        return
    
    time.sleep(1)
    sim.start()

    logger.info(f"{sim._format_time_pretty(time.monotonic() - sim.simulation_start_time)} Wait for simulation thread to fully terminate...\n")
    time.sleep(1)
    sim.wait_for_completion(timeout=10)
    time.sleep(1)
    capture.stop_capture()
    logger.info(f"{sim._format_time_pretty(time.monotonic() - sim.simulation_start_time)} Simulation terminated!\n")

def run(dot_file_path: str):
    """
    Start the Mininet network and the traffic generation

    Attributes:
        dot_file_path (str): path of the dot file
    """
    net, nat = setup(dot_file_path)

    logger.info('Starting network...\n')
    net.start()

    # It's good practice to wait a moment for the controller and switches to connect.
    logger.info('Wait for controller and switches to connect...\n')
    wait_time = 2
    logger.debug('  ┗  ', extra={'no_header': True})
    for i in range(wait_time):
        logger.debug(f'{wait_time - i}..', extra={'no_header': True})
        time.sleep(1)
    logger.debug(f'\n', extra={'no_header': True})
    
    logger.info(f'Network started!\n')
    start_simulation(net)

    # CLI(net) 

    teardown(net)

def setup_logger():
    """
    Configure the custom logger
    """
    # Custom format headers
    log_headers = {
        logging.DEBUG:   f"{LoggerColors.BOLD} *** [DEBUG   ]:{LoggerColors.RESET} %(msg)s",
        logging.INFO:    f"{LoggerColors.BOLD}{LoggerColors.BLUE} *** [INFO    ]:{LoggerColors.RESET} %(msg)s",
        logging.WARNING: f"{LoggerColors.BOLD}{LoggerColors.YELLOW} *** [WARNING ]:{LoggerColors.RESET} %(msg)s",
        logging.ERROR:   f"{LoggerColors.BOLD}{LoggerColors.RED} *** [ERROR   ]:{LoggerColors.RESET} %(msg)s",
        logging.CRITICAL:f"{LoggerColors.BOLD}{LoggerColors.MAGENTA} *** [CRITICAL]:{LoggerColors.RESET} %(msg)s",
    }

    # Set log level
    logger.setLevel(logging.INFO)

    # Create handler with custsom formatter
    handler = logging.StreamHandler()
    handler.terminator = ''
    custom_formatter = CustomFormatter(formats=log_headers)
    handler.setFormatter(custom_formatter)

    # Add custom handler
    if not logger.handlers:
        logger.addHandler(handler)

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
    
    setup_logger()
    # log.setLogLevel('info')
    run(topology_file)
