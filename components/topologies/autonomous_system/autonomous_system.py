from components.interfaces.interface import Interface
from components.topologies.topology import Topology, Switch, Router
import networkx as nx
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from typing import Iterable

from iptx_utils import NetworkError


class AutonomousSystem(Topology):
    def __init__(self, as_number: int, name: str, devices: Iterable[Switch | Router] = None, mpls: bool = True):
        super().__init__(as_number, devices)
        self.name: str = name
        self.mpls: bool = mpls
        self.reference_bw: int = 1      # Reference bandwidth in M bits/s

    def add_router(self, router: Router) -> None:

        super().add_router(router)

    def print_links(self) -> None:
        links = sorted(self._graph.edges(data=True), key=lambda link: link[2]["scr"])

        for edge in links:
            print(f"{edge[0]} ({edge[2]['d1_port']}) ---> {edge[1]} ({edge[2]['d2_port']})   SCR: {edge[2]['scr']:6d}, "
                  f"Network IP: {Interface.consistent_spacing_ip(edge[2]['network_address'])}, "
                  f"Bandwidth: {edge[2]['bandwidth']:8d} KB/s, External: {edge[2]['egp']}")

    def __update_reference_bw(self, new_bandwidth: int):    # new_bandwidth in k bits/s
        if (new_bandwidth // 1000) > self.reference_bw:
            self.reference_bw = new_bandwidth // 1000

    def update_ref_bw_rtrs(self) -> None:
        for router in self.get_all_routers():
            router.reference_bw = self.reference_bw

    def assign_network_ip_address(self, network_address: str,
                                  device_id1: str = None,
                                  device_id2: str = None,
                                  scr: int = None) -> None:

        network_addresses = [edge[2]["network_address"] for edge in self._graph.edges(data=True)
                             if "network_address" in edge[2]]

        if network_address in network_addresses:
            raise NetworkError(f"Network address '{network_address}' is already used in another network.")

        if device_id1 and device_id2:
            edge = self.get_link(device_id1, device_id2)
        elif scr:
            edge = self.get_link_by_key(scr)
        else:
            raise TypeError("Please provide either both device_id1 and device_id2, or just the SCR/key")

        edge[2]["network_address"] = network_address

        port1 = edge[2]["d1_port"]
        port2 = edge[2]["d2_port"]

        if isinstance(self[device_id1], Router) and isinstance(self[device_id2], Router):
            ip1, ip2 = RouterInterface.p2p_ip_addresses(network_address)
            self[device_id1].interface(port1).config(cidr=ip1)
            self[device_id2].interface(port2).config(cidr=ip2)

    def connect_devices(self, device_id1: str | int, port1: str, device_id2: str | int, port2: str,
                        scr: int = None, network_address: str = None, cable_bandwidth: int = None) -> None:

        self.print_log(f"Connecting devices {self[device_id1]} to {self[device_id2]}...")
        super().connect_devices(device_id1, port1, device_id2, port2, scr, cable_bandwidth)

        # Update the reference bandwidth
        new_ref_bandwidth: int = self.get_link(device_id1, device_id2)[2]["bandwidth"]
        self.__update_reference_bw(new_ref_bandwidth)

        # Links are identified using SCRs (Service Connection Request) in F@H instead of keys, so 'key'
        # is replaced with 'scr'
        self.get_link(device_id1, device_id2)[2]["scr"] = self.get_link(device_id1, device_id2)[2].pop("key")

        # Network address is given, so put it in
        if network_address:
            self.assign_network_ip_address(network_address, device_id1, device_id2)
        else:
            self.get_link(device_id1, device_id2)[2]["network_address"] = None

        # If MPLS is enabled, enable MPLS to all the routers
        if self.mpls:
            self[device_id1].interface(port1).mpls_enable()
            self[device_id2].interface(port2).mpls_enable()

        # This is an intra-autonomous connection, so EGP is always False
        self.get_link(device_id1, device_id2)[2]["egp"] = False



