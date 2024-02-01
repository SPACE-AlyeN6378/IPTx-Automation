from typing import Iterable, List, Any

import networkx as nx
import matplotlib.pyplot as plt
from components.nodes.switch import Switch, SwitchInterface
from components.nodes.router import Router
from components.interfaces.physical_interface import PhysicalInterface
from iptx_utils import NetworkError, NotFoundError
from list_helper import next_number


class Topology:
    def __init__(self, as_number: int, devices: Iterable[Switch | Router] = None):
        if devices is None:
            devices = []

        self.as_number = as_number
        self.__graph = nx.MultiGraph()
        self.add_devices(devices)

    def get_all_nodes(self) -> List[Switch | Router]:
        return list(self.__graph.nodes())

    def get_all_routers(self) -> List[Router]:
        return [node for node in self.__graph.nodes() if isinstance(node, Router)]

    def get_all_switches(self) -> List[Switch]:
        return [node for node in self.__graph.nodes() if isinstance(node, Switch)]

    def __getitem__(self, device_id_or_name: int | str) -> Switch | Router | None:
        for device in self.__graph.nodes():
            if device_id_or_name in [device.get_id(), device.hostname]:
                return device

        raise NotFoundError(f"ERROR in AS_NUM {self.as_number}: Device '{device_id_or_name}' "
                            f"invalid or not found")

    def add_switch(self, switch: Switch) -> None:
        if not isinstance(switch, Switch):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {switch.hostname} is not a switch")

        # If the ID is not given, then we add the default ID
        if switch.get_id() is None:
            all_ids = [device_.get_id() for device_ in self.__graph.nodes() if isinstance(device_.get_id(), int)]
            switch.update_id(next_number(all_ids, 1))

        if self.__graph.has_node(switch):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"hostname or ID. Please try a different name.")

        self.__graph.add_node(switch)

    def add_router(self, router: Router) -> None:
        if not isinstance(router, Router):
            raise TypeError(f"ERROR in AS_NUM {self.as_number}: Device {router.hostname} is not a router")

        if self.__graph.has_node(router):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: There's already a device with identical "
                               f"hostname or ID. Please try a different name.")

        self.__graph.add_node(router)

    def add_devices(self, devices: Iterable[Router | Switch]):
        for device in devices:
            if isinstance(device, Router):
                self.add_router(device)
            elif isinstance(device, Switch):
                self.add_switch(device)
            else:
                raise NetworkError(f"ERROR in AS_NUM {self.as_number}: Invalid device type {str(device)}")

    def remove_device(self, device: Switch | Router) -> None:
        if not self.__graph.has_node(device):
            raise NetworkError(f"ERROR in AS_NUM {self.as_number}: Device {device.hostname} not found in the topology, "
                               f"so cannot be removed.")

        self.__graph.remove_node(device)

    def remove_device_by_id(self, device_id: int | str):
        for device in self.get_all_nodes():
            if device_id == device.get_id():
                self.__graph.remove_node(device)
                break

    def connect_devices(self, device_id1: str | int, port1: str, device_id2: str | int, port2: str) -> None:
        ethernet_types = list(PhysicalInterface.BANDWIDTHS.keys())[1:5]
        if not (self[device_id1][port1].int_type in ethernet_types
                and self[device_id2][port2].int_type in ethernet_types):

            if self[device_id1][port1].int_type != self[device_id2][port2].int_type:
                raise ConnectionError(f"ERROR in AS_NUM {self.as_number}: Cannot "
                                      f"connect {str(self[device_id1][port1])} with "
                                      f"{str(self[device_id2][port2])}")

        self[device_id1].connect(port1, self[device_id2], port2)
        self[device_id2].connect(port2, self[device_id1], port1)
        self.__graph.add_edge(self[device_id1], self[device_id2])

    def show_plot(self):
        pos = nx.spring_layout(self.__graph)
        nx.draw(self.__graph, pos, with_labels=True, font_weight='bold', node_size=1000, node_color='red',
                font_color='black',
                font_size=10)

        plt.show()

