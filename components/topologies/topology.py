from typing import Iterable, List, Any, Tuple, Dict

import networkx as nx
import matplotlib.pyplot as plt
from components.devices.switch.switch import Switch
from components.devices.router.router import Router
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface

from iptx_utils import NetworkError, NotFoundError, smallest_missing_non_negative_integer

# Referenced Data Types
Edge = Tuple[Switch | Router, Switch | Router, Dict[str, Any]]


class Topology:
    def __init__(self, as_number: int, devices: Iterable[Switch | Router] = None):
        if devices is None:
            devices = []

        self.as_number = as_number
        self._graph = nx.Graph()
        self.add_devices(devices)

    # Ensures that a unique key is passed. If the number is not given, the smallest missing number is used instead
    def __auto_generate_key(self, number: int = None) -> int:
        keys = [edge[2]["key"] for edge in self._graph.edges(data=True) if "key" in edge[2]]
        keys.extend(edge[2]["scr"] for edge in self._graph.edges(data=True) if "scr" in edge[2])

        # If the number in the parameter is passed
        if number is not None:
            # If the number already exists, raise an error
            if number in keys:
                raise IndexError(f"Key ID '{number}' already exists at another link")

            return number

        else:    # The number is not passed in the scenario
            return smallest_missing_non_negative_integer(keys)

    def get_all_devices(self) -> List[Switch | Router]:
        return list(self._graph.nodes())

    def print_links(self) -> None:
        for edge in self._graph.edges(data=True):
            print(f"{edge[0]} ({edge[2]['d1_port']}) ---> {edge[1]} ({edge[2]['d2_port']})   Key: {edge[2]['key']:6d}, "
                  f"Bandwidth: {edge[2]['bandwidth']} KB/s")

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

    def get_link_by_key(self, key: int) -> None:
        for edge in self._graph.edges(data=True):
            if edge[2]['key'] == key:
                return edge

        raise IndexError(f"ERROR in AS_NUM {self.as_number}: Edge with key '{key}' not found")

    # def get_bandwidth(self, device_id1: str, device_id2: str):

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

    def add_router(self, router: Router) -> None:

        if not isinstance(router, Router):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {router.hostname} is not a router")

        if self._graph.has_node(router):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"ID {router.id()}. Please try a different one.")

        self._graph.add_node(router)

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
                        key: int = None, cable_bandwidth: int = None) -> None:

        key = self.__auto_generate_key(key)

        ethernet_types = list(PhysicalInterface.BANDWIDTHS.keys())[1:5]

        if not (self[device_id1].interface(port1).int_type in ethernet_types
                and self[device_id2].interface(port2).int_type in ethernet_types):

            if self[device_id1].interface(port1).int_type != self[device_id2].interface(port2).int_type:
                raise ConnectionError(f"ERROR in AS_NUM {self.as_number}: Cannot "
                                      f"connect {str(self[device_id1].interface(port1))} with "
                                      f"{str(self[device_id2].interface(port2))}")

        self[device_id1].interface(port1).connect_to(self[device_id2], port2, cable_bandwidth)
        self[device_id2].interface(port2).connect_to(self[device_id1], port1, cable_bandwidth)
        link_bandwidth = self[device_id1].interface(port1).bandwidth

        self._graph.add_edge(self[device_id1], self[device_id2], d1_port=port1, d2_port=port2,
                             key=key, bandwidth=link_bandwidth)

    def show_plot(self, layout: str = "spring"):
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

        nx.draw(self._graph, pos, with_labels=True, font_weight='bold', node_size=1000, node_color='skyblue',
                font_color='black',
                font_size=10)

        plt.show()
