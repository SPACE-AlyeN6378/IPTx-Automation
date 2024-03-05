from colorama import Fore

from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List, Set

from iptx_utils import print_warning, print_log, DeviceError


class Router(NetworkDevice):

    def __init__(self, router_id: str, hostname: str = "Router",
                 interfaces: Iterable[RouterInterface | Loopback] = None, ios_xr: bool = False) -> None:

        self.mpls_enabled: bool = True
        self.OSPF_PROCESS_ID: int = 65000
        # self.OSPF_MPLS_PROCESS_ID: int = 2500

        self.ios_xr: bool = ios_xr
        self.priority: int = 20  # Priority on a scale of 1 to 100

        # BGP properties
        self.as_number: int = 0
        self.route_reflector: bool = False
        self.ibgp_adjacent_router_ids: List[str] = []

        super().__init__(device_id=router_id, hostname=hostname)
        self.add_interface(Loopback(cidr=router_id, description=f"LOOPBACK-FHL-{hostname}"))
        self.add_interface(*interfaces)

        # Reference bandwidth
        self.reference_bw = self.get_max_bandwidth() // 1000

        # VRF
        self.provider_edge = True
        self.vrf_list: Dict[int, Dict[str, int | str]] = dict()
        self._basic_commands.update({
            "vrf": []
        })

        self.__routing_commands: Dict[str, List[str]] = {
            "ospf": [],
            "bgp": [],
            "mpls": []
        }

        self.__bgp_commands: dict[str, list[str]] = {
            "start": [],
            "id": [],
            "address_families": [],
            "ipv4_uni-cast": [],
            "vpn_v4": [],
            "neighbor_group": [],
            "neighbor": [],
            "redistribute": []
        }

    def __str__(self):
        name = super().__str__().replace("Device", "Router")
        if self.ios_xr:
            name = "XR " + name

        return name

    def __any_mpls_interfaces(self) -> bool:
        return any(interface.mpls_enabled for interface in self.all_phys_interfaces())

    # ********* GETTERS *********
    def interface(self, port: str) -> RouterInterface:
        return super().interface(port)

    def interface_range(self, *ports: str) -> List[RouterInterface]:
        return super().interface_range(*ports)

    def all_phys_interfaces(self) -> List[RouterInterface]:
        return super().all_phys_interfaces()

    def all_interfaces(self) -> List[RouterInterface | Loopback]:
        return super().all_interfaces()

    def add_interface(self, *new_interfaces: RouterInterface | Loopback) -> None:
        if not all(isinstance(interface, (RouterInterface, Loopback)) for interface in new_interfaces):
            raise TypeError("All interfaces should either be a RouterInterface or a Loopback")

        if self.ios_xr:
            for interface in new_interfaces:
                interface.xr_mode = True

        super().add_interface(*new_interfaces)

    def get_ints_by_ospf_area(self, area_number):
        return [interface for interface in self.all_interfaces() if interface.ospf_area == area_number]

    def get_all_areas(self) -> Set[int]:
        return set([interface.ospf_area for interface in self.all_interfaces()])

    # Shortcut to setting up the OSPF area numbers for each router interface
    def set_ospf_area(self, area_number, ports: List[str] | str) -> None:

        if isinstance(ports, str):
            self.interface(ports).ospf_area = area_number

        else:
            for interface in self.interface_range(*ports):
                interface.ospf_area = area_number

    def add_vrf(self, rd_number: int, name: str, import_target: int) -> None:
        if not self.provider_edge:
            raise DeviceError("This is not a provider edge router, so VRF cannot be configured in this device")

        if self.as_number == 0:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        self.vrf_list[rd_number] = {
            "name": name,
            "import_target": import_target
        }

        if self.ios_xr:
            self._basic_commands["vrf"].extend([
                f"vrf {name}",
                "address-family ipv4 unicast",
                f"import route-target {self.as_number}:{import_target}",
                f"export route-target {self.as_number}:{rd_number}",
                "exit",
                "exit"
            ])
        else:
            self._basic_commands["vrf"].extend([
                f"vrf {name}",
                f"rd {self.as_number}:{rd_number}",
                f"route-target export {self.as_number}:{rd_number}",
                f"route-target import {self.as_number}:{import_target}",
                "exit"
            ])

    def begin_igp_routing(self):
        # Configure OSPF for all interfaces
        for interface in self.all_phys_interfaces():
            # The interface should be connected to another router, and within autonomous system
            if isinstance(interface.remote_device, Router):
                if not interface.egp:
                    interface.ospf_config(process_id=self.OSPF_PROCESS_ID, p2p=interface.ospf_p2p)

        for interface in self.all_loopbacks():
            interface.ospf_config(process_id=self.OSPF_PROCESS_ID)

        # Generate Cisco command for initialization of router OSPF configuration
        self.__routing_commands["ospf"] = [
            f"router ospf {self.OSPF_PROCESS_ID}",  # Define the process ID
            f"router-id {self.id()}",  # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # Generate Cisco command
        # For IOS XR
        if self.ios_xr:
            for area_number in self.get_all_areas():
                self.__routing_commands["ospf"].append(f"area {area_number}")

                for interface in self.get_ints_by_ospf_area(area_number):
                    # If the physical interface is connected or is just a loopback
                    if interface.int_type == "Loopback":
                        self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())
                    elif interface.remote_device is not None and not interface.egp:
                        self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())

                self.__routing_commands["ospf"].append("exit")

        else:  # For IOS routers
            # All the EGP interfaces and loopbacks are configured as passive, in the OSPF section
            for interface in self.all_interfaces():
                if not interface.ospf_allow_hellos:
                    self.__routing_commands["ospf"].append(f"passive-interface {str(interface)}")

        self.__routing_commands["ospf"].append("exit")

    def __consolidate_bgp_commands(self) -> None:

        if self.ios_xr:
            keys = ["start", "id", "address_families", "neighbor_group", "ipv4_uni-cast",
                    "vpn_v4", "neighbor", "redistribute"]

            self.__bgp_commands["vpn_v4"].append("exit")    # To exit out of the neighbor-group command

        else:
            keys = ["start", "id", "neighbor", "vpn_v4", "redistribute"]

        for key in keys:
            if self.__bgp_commands[key]:
                self.__routing_commands["bgp"].extend(self.__bgp_commands[key])
                self.__bgp_commands[key].clear()

        self.__routing_commands["bgp"].append("exit")

    def begin_ibgp_routing(self) -> None:
        # Error check for any missing attributes
        if self.as_number == 0:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        if not self.ibgp_adjacent_router_ids:
            raise ValueError("No adjacent routers are assigned. Please assign a route reflector first.")

        # If there is no MPLS interfaces, print a WARNING message
        if not self.__any_mpls_interfaces() and self.vrf_list:
            print_warning("VRF is configured without any MPLS capabilities. MPLS is required for the VPN connection "
                          "to be established.")

        # Starting with the AS number and the ID
        self.__bgp_commands["start"] = [f"router bgp {self.as_number}"]
        self.__bgp_commands["id"] = [
            f"bgp router-id {self.id()}",
        ]

        if self.route_reflector:
            self.__bgp_commands["id"].append(f"bgp cluster-id {self.id()}")

        # In IOS XR Mode
        if self.ios_xr:
            # VPNv4 Communities
            self.__bgp_commands["address_families"] = [
                "address-family ipv4 unicast",
                "exit"
            ]

            if self.__any_mpls_interfaces():
                self.__bgp_commands["address_families"].extend([
                    "address-family vpnv4 unicast",
                    "exit"
                ])

                self.__bgp_commands["ipv4_uni-cast"] = ["address-family ipv4 labeled-unicast"]
                self.__bgp_commands["vpn_v4"] = ["address-family vpnv4 unicast"]

            else:
                self.__bgp_commands["ipv4_uni-cast"] = ["address-family ipv4 unicast"]

            if self.route_reflector:
                neighbor_group_name = "RR_TO_CLIENT"
                # Address-family in neighbor group
                self.__bgp_commands["ipv4_uni-cast"].extend([
                    "route-reflector-client",
                    "exit"
                ])
                if self.__any_mpls_interfaces():
                    self.__bgp_commands["vpn_v4"].extend([
                        "route-reflector-client",
                        "exit"
                    ])

            else:
                neighbor_group_name = "CLIENT_TO_RR"
                # Address-family in neighbor group
                self.__bgp_commands["ipv4_uni-cast"].extend([
                    "soft-reconfiguration inbound always",
                    "exit"
                ])
                if self.__any_mpls_interfaces():
                    self.__bgp_commands["vpn_v4"].extend([
                        "soft-reconfiguration inbound always",
                        "exit"
                    ])

            # Neighbor group establishment
            self.__bgp_commands["neighbor_group"] = [
                f"neighbor-group {neighbor_group_name}",
                f"remote-as {self.as_number}",
                f"update-source {self.loopback(0)}"
            ]

            # Assign neighbor group to each adjacent routers to establish neighbor
            for router_id in self.ibgp_adjacent_router_ids:
                self.__bgp_commands["neighbor"].extend([
                    f"neighbor {router_id}",
                    f"use neighbor-group {neighbor_group_name}",
                    "exit"
                ])

            # Redistribution, either through VRF or none
            if self.vrf_list:

                for rd_number, vrf in self.vrf_list.items():
                    self.__bgp_commands["redistribute"].extend([
                        f"vrf {vrf['name']}",
                        f"rd {self.as_number}:{rd_number}",
                        "address-family ipv4 unicast",
                        "label mode per-vrf",
                        "redistribute connected",
                        "exit", "exit"
                    ])
            else:
                self.__bgp_commands["address_families"].insert(1, "redistribute connected")

        # In IOS XE Mode
        else:
            # VPNv4 Communities
            if self.__any_mpls_interfaces():
                self.__bgp_commands["vpn_v4"] = ["address-family vpnv4"]

            # Iterating through each adjacent router ID
            for router_id in self.ibgp_adjacent_router_ids:
                # Neighborhood establishment
                self.__bgp_commands["neighbor"].extend([
                    f"neighbor {router_id} remote-as {self.as_number}",
                    f"neighbor {router_id} update-source {self.loopback(0)}",
                    f"neighbor {router_id} route-reflector-client"
                ])

                # VPNv4 Communities
                if self.__any_mpls_interfaces():
                    self.__bgp_commands["vpn_v4"].extend([
                        f"neighbor {router_id} activate",
                        f"neighbor {router_id} send-community extended"
                    ])

            if self.__any_mpls_interfaces():
                self.__bgp_commands["vpn_v4"].append("exit-address-family")

            # Redistribution, either through VRF or none
            if self.vrf_list:
                for vrf in self.vrf_list.values():
                    self.__bgp_commands["redistribute"].extend([
                        f"address-family ipv4 vrf {vrf['name']}",
                        "redistribute connected",
                        "exit-address-family"
                    ])
            else:
                self.__bgp_commands["redistribute"].append("redistribute connected")

        # Transfer all the BGP commands to a single list
        self.__consolidate_bgp_commands()

    def __generate_mpls_command(self) -> None:
        if self.__any_mpls_interfaces():
            if self.ios_xr:
                self.__routing_commands["mpls"] = [
                    "mpls ldp",
                    f"router-id {self.id()}"
                ]

                for interface in self.all_phys_interfaces():
                    if interface.mpls_enabled:
                        self.__routing_commands["mpls"].append(f"interface {str(interface)}")
                        self.__routing_commands["mpls"].append("exit")

                self.__routing_commands["mpls"].append("exit")

            else:
                # If MPLS is enabled in any interfaces, enable LDP synchronization
                if self.__any_mpls_interfaces():
                    self.__routing_commands["ospf"].insert(1, "mpls ldp sync")
                    self.__routing_commands["mpls"] = [
                        "mpls ldp router-id loopback0",
                        "mpls label protocol ldp"
                    ]

    def send_script(self) -> None:
        print_log("Building configuration...")

        # Start with 'configure terminal'
        script = ["configure terminal"]

        # Generate a script for any MPLS routing
        self.__generate_mpls_command()

        # Iterate through each cisco command by key
        for attr in self._basic_commands.keys():
            # Add the cisco commands to the script and clear it, so that it doesn't have to be
            # added again, until any of the attributes have changed
            script.extend(self._basic_commands[attr])
            self._basic_commands[attr].clear()

        # Iterate through each interface
        for interface in self.all_interfaces():
            script.extend(interface.generate_command_block())

        # Iterate through each routing command
        for attr in self.__routing_commands.keys():
            if self.__routing_commands[attr]:
                script.extend(self.__routing_commands[attr])
                self.__routing_commands[attr].clear()

        if self.ios_xr:
            script.append("commit")

        script.append("end")
        NetworkDevice.print_script(script, Fore.YELLOW)
