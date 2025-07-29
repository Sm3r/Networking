import networkx as nx
from mininet.topo import Topo
from mininet.log import info

class CustomTopology(Topo):
    """
    The topology of the network

    Attributes:
        path (string): path of the netowrk topology graphviz dot file
    """
    def __init__(self, path, **opts):
        super().__init__(**opts)

        # Load the Graphviz file into a NetworkX graph
        self.graph = nx.nx_agraph.read_dot(path)
        self.create_topology()

    """
    Generate the topology of the network
    """
    def create_topology(self):
        # Add nodes
        for node in self.graph.nodes():
            if node.startswith('s'):
                self.addSwitch(node)
            elif node.startswith('h'):
                self.addHost(node)
        
        # Add edges
        for u, v in self.graph.edges():
            self.addLink(u, v)

