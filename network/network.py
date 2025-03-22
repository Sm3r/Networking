from topology import Topology
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI

def setup_ftp_server(host):
    result = host.cmd("apt install --yes vsftpd")
    print(result)

def setup(net):
    hosts = net.hosts

    # Setup every host
    for i, host in enumerate(hosts):
        # Skip NAT host
        if "nat" in host.name:
            continue

        # Setup DNS for every host interface
        interfaces = host.cmd("ls /sys/class/net") 
        for intf in interfaces.split(' '):
            if host.name not in intf:
                continue
            host.cmd(f"resolvectl dns {intf} 8.8.8.8")
        host.cmd(f"systemctl restart systemd-resolved")

        print(f"{i}. {host.name}")

    # ftp_server = hosts[0]
    # setup_ftp_server(ftp_server)


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

    setup(net)
    net.start()


    if __name__ == "__main__":
        CLI(net)
    
    net.stop()

if __name__ == "__main__":
    run()
