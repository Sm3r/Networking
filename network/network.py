from topology import Topology
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI

def run():
    # Adjacency list for the switch topology
    switches = [
        [1],
        []
    ]
    # List of number of connected hosts for each switch (size of hosts must be the same of the size of switches)
    hosts = [2, 1]

    # Initialize Ryu controller
    controller = RemoteController('c1', '127.0.0.1')

    # Initialize mininet network
    topo = Topology(switches, hosts)
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        controller=controller,
        build=False,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink
    )

    # Build and start the network
    net.build()
    net.addNAT().configDefault()
    net.start()

    if __name__ == "__main__":
        CLI(net)
    
    net.stop()

if __name__ == "__main__":
    run()
