from typing import Iterable, List, Any

import networkx as nx
import matplotlib.pyplot as plt
from components.devices.switch.switch import Switch
from components.devices.router.router import Router
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface

from iptx_utils import NetworkError, NotFoundError, smallest_missing_non_negative_integer


class Topology:
    def __init__(self, as_number: int, devices: Iterable[Switch | Router] = None):
        if devices is None:
            devices = []

        self.as_number = as_number
        self.__graph = nx.Graph()
        self.add_devices(devices)

    # Ensures that a unique key is passed. If the number is not given, the smallest missing number is used instead
    def __process_key(self, number: int = None) -> int:
        keys = [edge[2] for edge in self.__graph.edges(keys=True)]

        if number is not None:
            if number in keys:
                raise ConnectionRefusedError(f"Key ID '{number}' already exists at another link")

            return number

        else:
            return smallest_missing_non_negative_integer(keys)

    def get_all_devices(self) -> List[Switch | Router]:
        return list(self.__graph.nodes())

    def get_all_routers(self) -> List[Router]:
        return [node for node in self.__graph.nodes() if isinstance(node, Router)]

    def get_all_switches(self) -> List[Switch]:
        return [node for node in self.__graph.nodes() if isinstance(node, Switch)]

    def __getitem__(self, device_id: str) -> Switch | Router:
        for device in self.__graph.nodes():
            if device_id == device.id():
                return device

        raise NotFoundError(f"ERROR in AS_NUM {self.as_number}: Device with ID '{device_id}' "
                            f"invalid or not found")

    def get_device(self, device_id: str) -> Switch | Router:
        for device in self.__graph.nodes():
            if device_id == device.id():
                return device

        raise NotFoundError(f"ERROR in AS_NUM {self.as_number}: Device with ID '{device_id}' "
                            f"invalid or not found")

    def get_link_by_key(self, key: int) -> Any:
        edge_attributes = nx.get_edge_attributes(self.__graph, 'key')
        for edge, corresponding_key in edge_attributes.items():
            if key == corresponding_key:
                return (*edge, self.__graph[edge[0]][edge[1]])

    def get_link_by_nodes(self, device_id1: str, device_id2: str) -> Any:
        return (self[device_id1], self[device_id2], self.__graph[self[device_id1]][self[device_id2]])

    def add_switch(self, switch: Switch) -> None:
        if not isinstance(switch, Switch):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {switch.hostname} is not a switch")

        # If the ID is not given, then we add the default ID
        if switch.id() is None:
            all_ids = [device_.id() for device_ in self.__graph.nodes() if isinstance(device_.id(), int)]
            switch.update_id(smallest_missing_non_negative_integer(all_ids, 1))

        if self.__graph.has_node(switch):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"hostname or ID. Please try a different name.")

        self.__graph.add_node(switch)

    def add_router(self, router: Router) -> None:

        if not isinstance(router, Router):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {router.hostname} is not a router")

        if self.__graph.has_node(router):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"ID {router.id()}. Please try a different one.")

        self.__graph.add_node(router)

    def add_devices(self, devices: Iterable[Router | Switch]):
        for device in devices:
            if isinstance(device, Router):
                self.add_router(device)
            elif isinstance(device, Switch):
                self.add_switch(device)
            else:
                raise TypeError(f"ERROR in AS_NUM {self.as_number}: Invalid device type {str(device)}")

    def remove_device(self, device: Switch | Router) -> None:
        if not self.__graph.has_node(device):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: Device {device.hostname} not found in the topology, "
                               f"so cannot be removed.")

        self.__graph.remove_node(device)

    def remove_device_by_id(self, device_id: str):
        for device in self.get_all_devices():
            if device_id == device.id():
                self.__graph.remove_node(device)
                break

    def connect_devices(self, device_id1: str | int, port1: str, device_id2: str | int, port2: str,
                        key: int = None, cable_bandwidth: int = None) -> None:

        # key = self.__process_key(key)

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

        self.__graph.add_edge(self[device_id1], self[device_id2], key=0, bandwidth=link_bandwidth)

    def show_plot(self, layout: str = "spring"):
        if layout.lower() == "spring":
            pos = nx.spring_layout(self.__graph)
        elif layout.lower() == "spectral":
            pos = nx.spectral_layout(self.__graph)
        elif layout.lower() == "circular":
            pos = nx.circular_layout(self.__graph)
        elif layout.lower() == "shell":
            pos = nx.shell_layout(self.__graph)
        elif layout.lower() == "kamada-kawai":
            pos = nx.kamada_kawai_layout(self.__graph)
        else:
            raise ValueError(f"Invalid layout type: {layout}")

        nx.draw(self.__graph, pos, with_labels=True, font_weight='bold', node_size=1000, node_color='skyblue',
                font_color='black',
                font_size=10)

        plt.show()
