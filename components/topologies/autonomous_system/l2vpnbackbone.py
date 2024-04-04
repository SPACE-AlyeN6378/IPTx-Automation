from components.topologies.autonomous_system.backbone import Backbone, Router, RouterInterface
import networkx as nx
from typing import Iterable


class L2VPNBackbone(Backbone):
    def __init__(self, as_number: int, name: str, devices: Iterable[Router] = None,
                 route_reflector_id: str = None):

        print(f"\n==================== IPTx L3VPN BACKBONE {as_number}: '{name}' ====================\n")
        super().__init__(as_number, name, devices)

        self.__vpn_graph = nx.Graph()
        self.__vlan_index = 2



