from typing import Iterable

import networkx as nx
import matplotlib.pyplot as plt
from components.nodes.switch import Switch, SwitchInterface
from iptx_utils import NetworkError


# Define a simple class
# Create an empty graph
class Topology():
    def __init__(self, as_number: int, devices: Iterable[Switch] = None):
        if devices is None:
            devices = []

        self.as_number = as_number
        self.__graph = nx.MultiGraph()

    def add_devices(self, device: Switch) -> None:
        if self.__graph.has_node(device):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical hostname. "
                               f"Please try a different name.")

        self.__graph.add_node(device)

    def remove_device(self, device: Switch):


G = nx.MultiGraph()

# Create instances of the Person class
switch1 = Switch(
    node_id=1,
    hostname="MySwitch1",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4, 5}
)

switch2 = Switch(
    node_id=2,
    hostname="MySwitch2",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4, 5}
)

switch3 = Switch(
    node_id=3,
    hostname="MySwitch3",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4, 5}
)

switch4 = Switch(
    node_id=4,
    hostname="MySwitch4",
    interfaces=[
        SwitchInterface("GigabitEthernet", "0/0"),
        SwitchInterface("GigabitEthernet", "0/1"),
        SwitchInterface("GigabitEthernet", "0/2"),
        SwitchInterface("GigabitEthernet", "0/3")
    ],
    vlan_ids={2, 3, 4, 5}
)

# Add nodes using class instances
G.add_nodes_from(range(1, 3))

# Add edges between the instances
G.add_edge(1, 2, link_id=123)
G.add_edge(2, 1, link_id=123)

# Draw the graph
pos = nx.spring_layout(G)
edge_labels = nx.get_edge_attributes(G, 'weight')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

nx.draw(G, pos, with_labels=True, font_weight='bold', node_size=1000, node_color='red', font_color='black',
        font_size=10)

# Display the graph
plt.show()
