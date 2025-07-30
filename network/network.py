#!/usr/bin/env python3

import sys
import os
import random
import time
import logging
from mininet import log
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from topology import CustomTopology
from trafficgen import TrafficGenerator
from customlogger.colors import LoggerColors
from customlogger.formatter import CustomFormatter

logger = logging.getLogger('networking')

#         elif choice == 'netcat':
#             h2.cmd('nc -l -p 5001 > /dev/null &')
#             h1.cmd('cat /dev/urandom | head -c 1M | nc 10.0.0.2 5001')

def setup_dns(net):
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

def setup_ftp_servers(net):
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

    setup_dns(net)
    setup_ftp_servers(net)
    return net, nat

def teardown(net):
    logger.debug('Stopping FTP servers...\n')
    logger.debug('  ┗  ', extra={'no_header': True})
    for server_name in net.topo.servers:
        net.get(server_name).cmd('kill %/usr/sbin/vsftpd')
        logger.debug(f'{server_name} ', extra={'no_header': True})
    logger.debug('\n', extra={'no_header': True})

def run(dot_file_path):
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
    traffic = TrafficGenerator()

    # TODO: Generate network traffic

    CLI(net) 

    traffic.wait_for_completion()

    teardown(net)

    logger.info('Stopping network...\n')
    net.stop()

def setup_logger():
    # Custom format headers
    log_headers = {
        logging.DEBUG:   f"{LoggerColors.BOLD} *** [DEBUG]:{LoggerColors.RESET} %(msg)s",
        logging.INFO:    f"{LoggerColors.CYAN} *** [INFO]:{LoggerColors.RESET} %(msg)s",
        logging.WARNING: f"{LoggerColors.YELLOW} *** [WARNING]:{LoggerColors.RESET} %(msg)s",
        logging.ERROR:   f"{LoggerColors.RED} *** [ERROR]:{LoggerColors.RESET} %(msg)s",
        logging.CRITICAL:f"{LoggerColors.BOLD}{LoggerColors.RED} *** [CRITICAL]:{LoggerColors.RESET} %(msg)s",
    }

    # Set log level
    logger.setLevel(logging.DEBUG)

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
