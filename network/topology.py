import networkx as nx
import logging
from mininet.topo import Topo
from customlogger.colors import LoggerColors

logger = logging.getLogger('networking')

class CustomTopology(Topo):
    """
    The topology of the network

    Attributes:
        path (string): path of the network topology graphviz dot file
    """
    def __init__(self, path, **opts):
        super().__init__(**opts)
        self.servers = []

        # Load the Graphviz file into a NetworkX graph
        graph = nx.nx_agraph.read_dot(path)
        self.create_topology(graph)

    """
    Generate the topology of the network

    Attributes:
        graph: NetworkX graph representing the topology of the network
    """
    def create_topology(self, graph):
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
        for u, v in graph.edges():
            self.addLink(u, v)

        logger.info(
            f"""Topology info:
  ┣  {LoggerColors.BOLD}Hosts:{LoggerColors.RESET} {len(self.hosts())}
  ┣  {LoggerColors.BOLD}Servers:{LoggerColors.RESET} {len(self.servers)}
  ┣  {LoggerColors.BOLD}Links:{LoggerColors.RESET} {len(self.links())}
  ┗  {LoggerColors.BOLD}Switches:{LoggerColors.RESET} {len(self.switches())}
"""
        )

