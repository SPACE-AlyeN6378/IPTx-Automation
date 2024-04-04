from components.topologies.topology import Topology, Switch, Router, Edge
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from typing import Iterable
from tabulate import tabulate

from iptx_utils import NetworkError, print_log, print_table, \
    smallest_missing_non_negative_integer


class Backbone(Topology):
    def __init__(self, as_number: int, name: str, devices: Iterable[Router] = None) -> None:

        if not all(isinstance(device, Router) for device in devices):
            raise TypeError("The backbone should only contain routers")

        super().__init__(as_number, devices)

        self.name: str = name
        self.reference_bw: int = 1  # Reference bandwidth in M bits/s

    def get_link_by_scr(self, scr: int) -> Edge:
        for edge in self._graph.edges(data=True):
            if edge[2]['scr'] == scr:
                return edge

        raise IndexError(f"Edge with key '{scr}' not found")

    def print_backbone_links(self) -> None:
        links = sorted(self._graph.edges(data=True), key=lambda link: link[2]["scr"])

        data = [[
            str(link[2]['scr']),
            f"{link[0]} ({link[2]['d1_port']}) ---> {link[1]} ({link[2]['d2_port']})",
            link[2]['network_address'],
            f"{link[2]['bandwidth']}"
        ] for link in links if not link[2]['external']]

        headers = ["SCR", "Source/Destination", "Network IP", "Bandwidth (KB/s)"]

        print()
        print_log("The following connections have been recognized within the backbone:")
        print(tabulate(data, headers=headers))
        print()

    def print_client_links(self) -> None:
        links = sorted(self._graph.edges(data=True), key=lambda link: link[2]["scr"])

        data = [[
            str(link[2]['scr']),
            f"{link[0]} ({link[2]['d1_port']}) ---> {link[1]} ({link[2]['d2_port']})",
            f"{link[2]['bandwidth']}"
        ] for link in links if link[2]['external']]

        headers = ["SCR", "Source/Destination", "Bandwidth (KB/s)"]

        print()
        print_log("The following external connections have been acknowledged from the clients:")
        print(tabulate(data, headers=headers))
        print()

    def __update_reference_bw(self, new_bandwidth: int) -> None:  # new_bandwidth in k bits/s
        if (new_bandwidth // 1000) > self.reference_bw:
            self.reference_bw = new_bandwidth // 1000

    # Ensures that a unique key is passed. If the number is not given, the smallest missing number is used instead
    def __assign_scr(self, device_id1: str, device_id2: str, number: int = None) -> None:
        keys = [edge[2]["scr"] for edge in self._graph.edges(data=True) if "scr" in edge[2]]

        # If the number in the parameter is passed
        if number is not None:
            # If the number already exists, raise an error
            if number in keys:
                raise IndexError(f"SCR '{number}' already exists at another link")

            scr = number

        else:  # The number is not passed
            scr = smallest_missing_non_negative_integer(keys)

        self.get_link(device_id1, device_id2)[2]["scr"] = scr

    def assign_network_ip_address(self, network_address: str,
                                  device_id1: str = None, device_id2: str = None,
                                  scr: int = None) -> None:

        # (BKB => Backbone)
        bkb_network_addresses = [edge[2]["network_address"] for edge in self._graph.edges(data=True)
                                 if "network_address" in edge[2] and not edge[2]["external"]]

        if network_address in bkb_network_addresses:
            raise NetworkError(f"Network address '{network_address}' is already used in "
                               f"another network in the backbone.")

        # If any parameters are passed
        if device_id1 and device_id2:
            edge = self.get_link(device_id1, device_id2)
        elif scr:
            edge = self.get_link_by_scr(scr)
        else:
            raise TypeError("Please provide either both device_id1 and device_id2, or just the SCR/key")

        port1 = edge[2]["d1_port"]
        port2 = edge[2]["d2_port"]

        ip1, ip2 = RouterInterface.p2p_ip_addresses(network_address)

        # Assign the IP address to Device 1
        if isinstance(self[device_id1], Router):
            self[device_id1].interface(port1).config(cidr=ip1)

        # Assign the IP address to Device 2
        if isinstance(self[device_id2], Router):
            self[device_id2].interface(port2).config(cidr=ip2)

        if isinstance(self[device_id1], Router) or isinstance(self[device_id2], Router):
            edge[2]["network_address"] = network_address

    def connect_devices(self, device_id1: str, port1: str, device_id2: str, port2: str,
                        scr: int = None, cable_bandwidth: int = None) -> None:

        super().connect_devices(device_id1, port1, device_id2, port2, cable_bandwidth)

        # Assign the SCRs
        self.__assign_scr(device_id1, device_id2, scr)  # This is used to check whether the SCR is already in

    def connect_internal_devices(self, device_id1: str, port1: str, device_id2: str, port2: str,
                                 network_address: str = None, scr: int = None, cable_bandwidth: int = None) -> None:

        if not network_address:
            raise NetworkError("IP Network address is required for link identification")

        if self[device_id1].as_number != self[device_id2].as_number:
            raise NetworkError(f"Unequal AS Numbers for {device_id1} and {device_id2}")

        self.print_log(f"Connecting backbone devices {self[device_id1]} to {self[device_id2]}...")
        self.connect_devices(device_id1, port1, device_id2, port2, scr, cable_bandwidth)

        # Put in the network IP address
        self.assign_network_ip_address(network_address, device_id1, device_id2)

        # Update the reference bandwidth
        new_ref_bandwidth: int = self.get_link(device_id1, device_id2)[2]["bandwidth"]
        self.__update_reference_bw(new_ref_bandwidth)

        # Enable MPLS to routers, if both the routers are within the same autonomous system
        self[device_id1].interface(port1).mpls_enable()
        self[device_id2].interface(port2).mpls_enable()

        # Configure the description for both the interfaces
        self[device_id1].interface(port1).config(description=f"BACKBONE_P2P_CONN_WITH::{self[device_id2]}")
        self[device_id2].interface(port2).config(description=f"BACKBONE_P2P_CONN_WITH::{self[device_id1]}")

        # They are internal connections
        self.get_link(device_id1, device_id2)[2]["external"] = False

    def connect_client(self, client_device: Router | Switch, client_port: str,
                       bkb_router_id: str | int, bkb_router_port: str, client_group: str,
                       cable_bandwidth: int = None):

        self.print_log(f"Requesting external connection of Client {str(client_device)} to the backbone...")

        # Add the client to the topology
        if isinstance(client_device, Router):
            # First, check if the AS numbers are different or not
            if client_device.as_number == self[bkb_router_id].as_number:
                raise NetworkError(f"This is for external routing, so the AS number of the client "
                                   f"{client_device.as_number} should not match the AS number of the backbone.")

            self.add_router(client_device, is_guest=True)

        elif isinstance(client_device, Switch):
            self.add_switch(client_device)

        self.connect_devices(bkb_router_id, bkb_router_port, client_device.id(), client_port, cable_bandwidth)

        # Switch the interfaces to EGP on both sides, since it's an external route
        self[client_device.id()].interface(client_port).egp = True
        self[bkb_router_id].interface(bkb_router_port).egp = True
        self.get_link(client_device.id(), bkb_router_id)[2]["external"] = True

        # Configure the description for both the interfaces
        (self[client_device.id()].interface(client_port)
         .config(description=f"BACKBONE_CONNECTION_WITH_{self[bkb_router_id]}_AS:{self.as_number}"))
        (self[bkb_router_id].interface(bkb_router_port)
         .config(description=f"CLIENT_CONNECTION_WITH::{self[client_device.id()]}"))

    def get_all_client_devices(self) -> list[Router | Switch]:
        return ([device for device in self.get_all_routers() if device.as_number != self.as_number]
                + self.get_all_switches())

    def begin_internal_routing(self) -> None:
        for router in self.get_all_routers():

            if router.as_number == self.as_number:
                print_log(f"Beginning route in {str(router)}...")
                router.reference_bw = self.reference_bw
                router.begin_internal_routing()
