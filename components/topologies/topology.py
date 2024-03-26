from typing import Iterable, List, Any, Tuple, Dict

import networkx as nx
import matplotlib.pyplot as plt
from components.devices.switch.switch import Switch
from components.devices.router.router import Router
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface

from iptx_utils import NetworkError, NotFoundError, smallest_missing_non_negative_integer, print_log, print_success

# Referenced Data Types
Edge = Tuple[Switch | Router, Switch | Router, Dict[str, Any]]


class Topology:
    def __init__(self, as_number: int, devices: Iterable[Switch | Router] = None):
        if devices is None:
            devices = []

        self.as_number = as_number
        self._graph = nx.Graph()
        self.add_devices(devices)

    def print_log(self, text: str) -> None:
        print_log(f"AS {self.as_number}: {text}")

    def get_all_devices(self) -> List[Switch | Router]:
        return list(self._graph.nodes())

    def get_all_routers(self) -> List[Router]:
        return [node for node in self._graph.nodes() if isinstance(node, Router)]

    def get_all_switches(self) -> List[Switch]:
        return [node for node in self._graph.nodes() if isinstance(node, Switch)]

    def __getitem__(self, device_id: str) -> Switch | Router:
        for device in self._graph.nodes():
            if device_id == device.id():
                return device

        raise NotFoundError(f"ERROR in AS_NUM {self.as_number}: Device with ID '{device_id}' "
                            f"invalid or not found")

    def get_device(self, device_id: str) -> Switch | Router:
        for device in self._graph.nodes():
            if device_id == device.id():
                return device

        raise NotFoundError(f"ERROR in AS_NUM {self.as_number}: Device with ID '{device_id}' "
                            f"invalid or not found")

    def get_link(self, device_id1: str, device_id2: str) -> Edge:
        return self[device_id1], self[device_id2], self._graph[self[device_id1]][self[device_id2]]

    def add_switch(self, switch: Switch) -> None:
        if not isinstance(switch, Switch):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {switch.hostname} is not a switch")

        # If the ID is not given, then we add the default ID
        if switch.id() is None:
            all_ids = [device_.id() for device_ in self._graph.nodes() if isinstance(device_.id(), int)]
            switch.update_id(smallest_missing_non_negative_integer(all_ids, 1))

        if self._graph.has_node(switch):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"hostname or ID. Please try a different name.")

        self._graph.add_node(switch)
        print_success(f"{str(switch)} added!")

    def add_router(self, router: Router, is_guest: bool = False) -> None:

        if not is_guest:
            router.as_number = self.as_number

        if not isinstance(router, Router):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {router.hostname} is not a router")

        if self._graph.has_node(router):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"ID {router.id()}. Please try a different one.")

        self._graph.add_node(router)

        if is_guest:
            print_success(f"{str(router)} added as a client!")
        else:
            print_success(f"{str(router)} added!")

    def add_devices(self, devices: Iterable[Router | Switch]):
        for device in devices:
            if isinstance(device, Router):
                self.add_router(device)
            elif isinstance(device, Switch):
                self.add_switch(device)
            else:
                raise TypeError(f"ERROR in AS_NUM {self.as_number}: Invalid device type {str(device)}")

    def remove_device(self, device: Switch | Router) -> None:
        if not self._graph.has_node(device):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: Device {device.hostname} not found in the topology, "
                               f"so cannot be removed.")

        self._graph.remove_node(device)

    def remove_device_by_id(self, device_id: str):
        for device in self.get_all_devices():
            if device_id == device.id():
                self._graph.remove_node(device)
                break

    def connect_devices(self, device_id1: str, port1: str, device_id2: str, port2: str,
                        cable_bandwidth: int = None) -> None:

        ethernet_types = list(PhysicalInterface.BANDWIDTHS.keys())[1:5]

        # Should be of the same interface type
        if not (self[device_id1].interface(port1).int_type in ethernet_types
                and self[device_id2].interface(port2).int_type in ethernet_types):

            if self[device_id1].interface(port1).int_type != self[device_id2].interface(port2).int_type:
                raise ConnectionError(f"Incompatible interface types: Cannot connect "
                                      f"{str(self[device_id1].interface(port1))} with "
                                      f"{str(self[device_id2].interface(port2))}")

        self[device_id1].interface(port1).connect_to(self[device_id2], port2, cable_bandwidth)
        self[device_id2].interface(port2).connect_to(self[device_id1], port1, cable_bandwidth)
        link_bandwidth = self[device_id1].interface(port1).bandwidth

        self._graph.add_edge(self[device_id1], self[device_id2], d1_port=port1, d2_port=port2,
                             bandwidth=link_bandwidth)

    def disconnect_devices(self, device_id1: str, device_id2: str):
        self._graph.remove_edge(self[device_id1], self[device_id2])

    def show_topology_graph(self, layout: str = "spring"):
        if layout.lower() == "spring":
            pos = nx.spring_layout(self._graph)
        elif layout.lower() == "spectral":
            pos = nx.spectral_layout(self._graph)
        elif layout.lower() == "circular":
            pos = nx.circular_layout(self._graph)
        elif layout.lower() == "shell":
            pos = nx.shell_layout(self._graph)
        elif layout.lower() == "kamada-kawai":
            pos = nx.kamada_kawai_layout(self._graph)
        else:
            raise ValueError(f"Invalid layout type: {layout}")

        node_colors = [node.node_color for node in self._graph.nodes()]

        nx.draw(self._graph, pos, with_labels=True, font_weight='bold', node_color=node_colors, node_size=1000,
                font_color='black',
                font_size=10)

        plt.show()
