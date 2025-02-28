from mininet.topo import Topo
from mininet.link import TCLink


class Topology(Topo):
    def __init__(self, switches, hosts):
        self.switches_topology = switches
        self.hosts_per_switch = hosts
        super().__init__()

    def build(self):
        self.switches = []
        self.hosts = []

        # Create and link switches
        for i, switch in enumerate(self.switches_topology):
            self.switches.append(self.addSwitch('s' + str(i)))

        for i, switch in enumerate(self.switches_topology):
            for s in switch:
                s1 = self.switches[i]
                s2 = self.switches[s]
                self.addLink(s1, s2, cls=TCLink, bw=40, delay='15ms')

        # Create and link hosts
        cnt = 0
        for i, host_count in enumerate(self.hosts_per_switch):
            self.hosts.append([])
            for h in range(host_count):
                cnt += 1
                host = self.addHost(
                    "h" + str(cnt),
                    mac='00:00:00:00:00:0' + str(cnt)
                )
                self.hosts[i].append(host)
                self.addLink(self.switches[i], host,
                             cls=TCLink, bw=40, delay='15ms')
