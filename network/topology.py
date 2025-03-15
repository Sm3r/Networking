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
        self._switches = []
        self._hosts = []

        # Create and link switches
        for i, switch in enumerate(self.switches_topology):
            self._switches.append(self.addSwitch('s' + str(i)))

        for i, switch in enumerate(self.switches_topology):
            for s in switch:
                s1 = self._switches[i]
                s2 = self._switches[s]
                self.addLink(s1, s2, cls=TCLink, bw=40, delay='15ms')

        # Create and link hosts
        cnt = 0
        for i, host_count in enumerate(self.hosts_per_switch):
            self._hosts.append([])
            for h in range(host_count):
                cnt += 1
                host = self.addHost(
                    "h" + str(cnt),
                    mac='00:00:00:00:00:0' + str(cnt)
                )
                self._hosts[i].append(host)
                self.addLink(self._switches[i], host,
                             cls=TCLink, bw=40, delay='15ms')
