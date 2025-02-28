from mininet.topo import Topo
from mininet.link import TCLink


class Topology(Topo):
    def build(self, switches, hosts):
        self.switches = []
        self.hosts = []

        # Create and link switches
        for i, switch in enumerate(switches):
            self.switches.append(self.addSwitch('s' + str(i)))

        for i, switch in enumerate(switches):
            for s in switch:
                s1 = self.switches[i]
                s2 = self.switches[s]
                self.addLink(s1, s2, cls=TCLink, bw=40, delay='15ms')

        # Create and link hosts
        cnt = 0
        for i, host_count in enumerate(hosts):
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
