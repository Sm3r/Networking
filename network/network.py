
import os
import sys
import time
import threading
from typing import Tuple
import numpy as np
import multiprocessing as mp

from mininet.cli import CLI
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.nodelib import NAT

from capture.packetsniffer import PacketSniffer
from logger import setup_logger
from simulation.simulation import Simulation
from topology import CustomTopology

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from train.realtime_predict import LivePredictor, realtime_plot_worker

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
def _setup_simulation_common(net: Mininet, traffic_distribution_path: str = None):
    if traffic_distribution_path is None:
        traffic_distribution_path = 'resources/distributions/traffic_signal.csv'
    
    HOURS = 1
    AVG_PACKETS_PER_MINUTE = 720
    total_duration = HOURS * 60 * 60
    total_requests = (AVG_PACKETS_PER_MINUTE / 60) * total_duration

    sim = Simulation(
        net=net,
        traffic_distribution_csv_path=traffic_distribution_path,
        website_list_path='resources/website-list.json',
        file_list_path='resources/file-list.json',
        start_time_of_day=np.random.randint(0, 86400),
        total_requests_count=total_requests,
        total_duration=total_duration,
        is_real_time=True,
        time_step=1
    )
    capture = PacketSniffer(simulation=sim, interface='any')
    
    try:
        capture.start_capture(output_filename='simple')
    except Exception as e:
        return None, None
    
    return sim, capture


def start_simulation(net: Mininet, traffic_distribution_path: str = None):
    sim, capture = _setup_simulation_common(net, traffic_distribution_path)
    if sim is None:
        return

    time.sleep(5)
    sim_thread = threading.Thread(target=sim.start, name='simulation-main')
    sim_thread.start()

    logger.info(f"{sim._format_time_pretty(sim.get_time())} Wait for simulation thread to fully terminate...\n")
    time.sleep(5)
    sim_thread.join()
    sim.wait_for_completion(timeout=None)
    time.sleep(5)
    capture.stop_capture()
    logger.info(f"{sim._format_time_pretty(sim.get_time())} Simulation terminated!\n")

def start_simulation_live_prediction(net: Mininet, traffic_distribution_path: str = None):
    sim, capture = _setup_simulation_common(net, traffic_distribution_path)
    if sim is None:
        return

    predictor = LivePredictor(sniffer=capture, simulation=sim)
    
    time.sleep(5)

    # 1. Start the separate Plotting Process
    plot_queue = mp.Queue()
    plot_process = mp.Process(target=realtime_plot_worker, args=(plot_queue,))
    plot_process.start()

    # 2. Start the Predictor Thread, passing it the queue
    predictor = LivePredictor(sniffer=capture, simulation=sim, plot_queue=plot_queue)
    predictor.start()
    
    # Start simulation
    sim.start()

    logger.info(f"{sim._format_time_pretty(sim.get_time())} Wait for simulation thread to fully terminate...\n")
    time.sleep(5)
    sim.wait_for_completion(timeout=None)
    time.sleep(5)
    
    # 3. Clean Shutdown
    predictor.stop()
    capture.stop_capture()
    
    # Send the kill signal to the plot window and wait for it to close
    plot_queue.put((None, None, None))
    plot_process.join(timeout=5)
    
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
def run(dot_file_path: str, live_pred: bool = False, traffic_distribution_path: str = None):

    net, nat = setup(dot_file_path)

    logger.info('Starting network...\n')
    net.start()
    net.topo.set_latency(net)
    time.sleep(2)
    
    logger.info(f'Network started!\n')
    
    if live_pred:
        start_simulation_live_prediction(net, traffic_distribution_path)
    else:
        start_simulation(net, traffic_distribution_path)

    # CLI(net) 

    teardown(net)

if __name__ == '__main__':
    # Check for the topology file argument
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print(f"Usage: sudo python3 {sys.argv[0]} [topology.dot] [--live] [distribution.csv]")
        sys.exit(1)

    # Ensure the topology file exists
    topology_file = sys.argv[1]
    if not os.path.isfile(topology_file):
        print(f"Error: Topology file not found at '{topology_file}'")
        sys.exit(1)
    
    # Check for optional parameters
    live_pred = False
    traffic_distribution_path = None
    
    for i in range(2, len(sys.argv)):
        if sys.argv[i] == '--live':
            live_pred = True
        elif sys.argv[i].endswith('.csv'):
            traffic_distribution_path = sys.argv[i]
        else:
            print(f"Error: Unknown parameter '{sys.argv[i]}'. Use '--live' or provide a CSV file path.")
            sys.exit(1)
    
    # log.setLogLevel('info')
    run(topology_file, live_pred, traffic_distribution_path)
