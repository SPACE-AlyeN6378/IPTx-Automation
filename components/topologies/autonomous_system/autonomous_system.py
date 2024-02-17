from components.topologies.topology import Topology, Switch, Router
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from typing import Iterable


class AutonomousSystem(Topology):
    def __init__(self, as_number: int, name: str, devices: Iterable[Switch | Router] = None):
        super().__init__(as_number, devices)
        self.name = name
        self.reference_bw: int = 1      # Reference bandwidth in M bits/s

    def __update_reference_bw(self, new_bandwidth: int):    # new_bandwidth in k bits/s
        if (new_bandwidth // 1000) > self.reference_bw:
            self.reference_bw = new_bandwidth // 1000

    def connect_devices(self, device_id1: str | int, port1: str, device_id2: str | int, port2: str,
                        key: int = None, network_address: str = None, cable_bandwidth: int = None) -> None:

        super().connect_devices(device_id1, port1, device_id2, port2, key, cable_bandwidth)
        # print(self._graph[self[device_id1]][self[device_id2]][self[device_id2]])

        if network_address:
            if isinstance(self[device_id1], Router) and isinstance(self[device_id2], Router):
                ip1, ip2 = RouterInterface.p2p_ip_addresses(network_address)
                self[device_id1].interface(port1).config(cidr=ip1)
                self[device_id2].interface(port2).config(cidr=ip2)




