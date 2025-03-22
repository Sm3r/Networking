from mininet.topo import Topo
from mininet.link import TCLink


class Topology(Topo):
    """
    The topology of the network

    Attributes:
        switches_topology ([[int]]): adjaceny list of switches
        hosts_per_switch ([int]): list of the number of hosts for each switch (the index in the list corresponds to the switch index) 
    """

    def __init__(self, switches, hosts):
        """
        Initialize the topology of the network

        Parameters:
            switches ([[int]]): adjaceny list of switches
            hosts ([int]): list of the number of hosts for each switch (the index in the list corresponds to the switch index) 
        """
        self.switches_topology = switches
        self.hosts_per_switch = hosts
        super().__init__()

    def build(self):
        """
        Build a new network from the previously given topology
        """

        # Create and link switches
        switches = []
        for i, switch in enumerate(self.switches_topology):
            switches.append(self.addSwitch('s' + str(i)))

        for i, switch in enumerate(self.switches_topology):
            for s in switch:
                s1 = switches[i]
                s2 = switches[s]
                self.addLink(s1, s2, cls=TCLink, bw=40, delay='15ms')

        # Create and link hosts
        cnt = 0
        for i, host_count in enumerate(self.hosts_per_switch):
            for h in range(host_count):
                cnt += 1
                hostname = self.addHost(
                    f"h{i}_{h}",
                    mac='00:00:00:00:00:0' + str(cnt)
                )
                self.addLink(switches[i], hostname,
                             cls=TCLink, bw=40, delay='15ms')
