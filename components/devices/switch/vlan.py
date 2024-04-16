from components.interfaces.interface import Interface
import networkx as nx
from typing import List, TYPE_CHECKING
from matplotlib import pyplot as plt

from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface

if TYPE_CHECKING:
    from components.interfaces.physical_interfaces.router_interface import RouterInterface


# ENUMS

class VLAN:

    @staticmethod
    def valid_id_check(vlan_id: int):
        # VLAN 4095 is a special VLAN used to represent a "wildcard" or "unassigned" VLAN.
        if 1 <= vlan_id <= 4095:
            if vlan_id == 4095:
                raise ConnectionError("VLAN 4095 is a special VLAN used to represent a \"wildcard\" or \"unassigned\" "
                                      "VLAN. Rather serves as a placeholder for certain configuration or management "
                                      "purposes.")

        else:
            raise ValueError(f"Invalid ID '{vlan_id}' - The VLAN ID must be between 2 and 4094")

    def __init__(self, vlan_id: int, name: str = None, cidr: str = None, color: str = "gray") -> None:
        VLAN.valid_id_check(vlan_id)
        self.vlan_id = vlan_id
        self.name = name
        self.vlan_as_interface = Interface("VLAN", vlan_id, cidr)  # For SVI routing
        self.assigned_routers: set[PhysicalInterface] = set()

        self._stp_primary_device = None
        self.pseudowire_graph = nx.Graph()
        self.color = color

    def config(self, name: str = None, cidr: str = None) -> None:
        if name:
            self.name = name

        if cidr:
            self.vlan_as_interface.config(cidr=cidr)

    # For switches =======================================
    def generate_init_cmd(self) -> List[str]:
        return [
            f"vlan {self.vlan_id}",
            f"name {self.name}",
            "exit"
        ]

    def generate_interface_cmd(self) -> List[str]:
        configs = self.vlan_as_interface.generate_config()
        configs.insert(-1, "no shutdown")
        return configs

    # For L2VPN pseudo-wire connection ===================
    def establish_pseudowire(self, interface1: 'RouterInterface', interface2: 'RouterInterface') -> None:
        description = f"To VLAN-{self.vlan_id}::{self.name}"
        interface1.pseudowire_config(self.vlan_id, interface2.device_id, description)
        interface2.pseudowire_config(self.vlan_id, interface1.device_id, description)

        self.pseudowire_graph.add_node(interface1, rtr_id=interface1.device_id)
        self.pseudowire_graph.add_node(interface2, rtr_id=interface2.device_id)
        self.pseudowire_graph.add_edge(interface1, interface2, description=description)

    def show_pseudowire_graph(self) -> None:
        pos = nx.spring_layout(self.pseudowire_graph)  # Positions for all nodes
        nx.draw(self.pseudowire_graph, pos, with_labels=True,
                labels={node_id: f"{node_id} ({data["rtr_id"]})" for node_id, data in
                        self.pseudowire_graph.nodes(data=True)},
                width=2, node_size=1000)
        plt.show()
