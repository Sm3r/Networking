import networkx as nx
import logging
from mininet.topo import Topo
from customlogger.colors import LoggerColors
from typing import Any

logger = logging.getLogger('networking')

class CustomTopology(Topo):
    """
    The topology of the network
    """
    def __init__(self, path: str, **opts: Any):
        """
        Parse the dot file and create the network topology

        Attributes:
            path (string): path of the network topology graphviz dot file
            opts (Any): additional arguments
        """
        super().__init__(**opts)
        self.servers = []
        self.latencies = []

        # Load the Graphviz file into a NetworkX graph
        graph = nx.nx_agraph.read_dot(path)
        self.create_topology(graph)

    def create_topology(self, graph: nx.Graph):
        """
        Generate the topology of the network

        Attributes:
            graph (nx.Graph): NetworkX graph representing the topology of the network
        """
        # Add nodes
        for node, attrs in graph.nodes(data=True):
            if node.startswith('s'):
                self.addSwitch(node)
            elif node.startswith('h'):
                self.addHost(node)

                # Append host marked as servers
                if attrs.get('type') == 'server':
                    self.servers.append(node)
        
        # Add edges
        for u, v, attrs in graph.edges(data=True):
            self.addLink(u, v)

            # Save latency to apply after network has started
            latency = attrs.get('latency')
            if latency:
                self.latencies.append({
                    'host1': u,
                    'host2': v,
                    'latency': latency
                })

        logger.info(
            f"""Topology info:
  ┣  {LoggerColors.BOLD}Hosts:{LoggerColors.RESET} {len(self.hosts())}
  ┣  {LoggerColors.BOLD}Servers:{LoggerColors.RESET} {len(self.servers)}
  ┣  {LoggerColors.BOLD}Links:{LoggerColors.RESET} {len(self.links())}
  ┗  {LoggerColors.BOLD}Switches:{LoggerColors.RESET} {len(self.switches())}
"""
        )

    def set_latency(self, net):
        """
        Set the latency for each link of the network

        Attributes:
            net (Mininet): a Mininet network
        """
        for target in self.latencies:
            h1 = net.get(target['host1'])
            h2 = net.get(target['host2'])
            latency = target['latency']

            # Find the interfaces connecting the two nodes
            intf1, intf2 = None, None
            for intf in h1.intfList():
                if intf.link and intf.link.intf2.node == h2:
                    intf1 = intf
                    intf2 = intf.link.intf2
                    break

            if not intf1 or not intf2:
                logger.warning(f'Could not find a direct link between {h1.name} and {h2.name}\n')
                return

            logger.debug(f'Found link: {intf1.name} <--> {intf2.name}\n')

            command = 'tc qdisc {} dev {} root netem delay {}'

            res = h1.cmd(command.format('change', intf1.name, latency))
            if 'Error' in res:
                h1.cmd(command.format('add', intf1.name, latency))

            res = h2.cmd(command.format('change', intf2.name, latency))
            if 'Error' in res:
                h2.cmd(command.format('add', intf2.name, latency))

            logger.info(f'Set latency to {latency}ms on link {h1.name}--{h2.name}\n')
