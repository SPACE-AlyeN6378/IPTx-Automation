from colorama import Fore

from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List, Set
from enum import Enum

from iptx_utils import print_warning, print_log, DeviceError, NetworkError


class VRFKey(Enum):
    NAME = 'name',
    IMPORT = 'import'


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
        self.vrfs: dict[int, dict[VRFKey, str | set[int]]] = dict()

        self.__vrf_commands: dict[int, list[str]] = dict()
        self._basic_commands.update({
            "vrf": []
        })

        self.__routing_commands: Dict[str, List[str]] = {
            "route-policy": [],
            "ospf": [],
            "bgp": [],
            "mpls": []
        }

        self.__bgp_commands: dict[str, list[str]] = {
            "start": [],
            "id": [],
            "address_families": [],
            "ipv4_unicast": [],
            "vpn_v4": [],
            "neighbor_group": [],
            "neighbor": [],
            "ebgp": []
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

    def add_vrf(self, rd_number: int, name: str) -> None:
        if not self.provider_edge:
            raise DeviceError("This is not a provider edge router, so VRF cannot be configured in this device")

        if self.as_number == 0:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        self.vrfs[rd_number] = {VRFKey.NAME: name, VRFKey.IMPORT: []}

        if self.ios_xr:
            self.__vrf_commands[rd_number] = [
                f"vrf {name}",
                "address-family ipv4 unicast",
                f"export route-target {self.as_number}:{rd_number}",
                "exit",
                "exit"
            ]
        else:
            self.__vrf_commands[rd_number] = [
                f"vrf definition {name}",
                f"rd {self.as_number}:{rd_number}",
                "address-family ipv4 unicast",
                f"route-target export {self.as_number}:{rd_number}",
                "exit",
                "exit",
            ]

    def set_route_targets(self, rd_number: int, *rds_to_be_imported: int) -> None:
        self.vrfs[rd_number][VRFKey.IMPORT] |= set(rds_to_be_imported)

        if not self.__vrf_commands[rd_number]:
            if self.ios_xr:
                self.__vrf_commands[rd_number] = [
                    f"vrf {self.vrfs[rd_number][VRFKey.NAME]}",
                    "address-family ipv4 unicast",
                    "exit",
                    "exit"
                ]
            else:
                self.__vrf_commands[rd_number].extend([
                    f"vrf definition {self.vrfs[rd_number][VRFKey.NAME]}",
                    "address-family ipv4 unicast",
                    "exit",
                    "exit",

                ])

        for remote_rd in rds_to_be_imported:
            if self.ios_xr:
                command = f"export route-target {self.as_number}:{remote_rd}"
            else:
                command = f"route-target export {self.as_number}:{remote_rd}"

            self.__vrf_commands[rd_number].insert(-2, command)

    def remove_vrf(self, rd_number: int) -> None:
        removed_vrf = self.vrfs.pop(rd_number)

        if self.ios_xr:
            self.__vrf_commands[rd_number] = [f"no vrf {removed_vrf[VRFKey.NAME]}"]
        else:
            self.__vrf_commands[rd_number] = [f"no vrf definition {removed_vrf[VRFKey.NAME]}"]

    def __consolidate_vrf_commands(self) -> None:
        for commands in self.__vrf_commands.values():
            if commands:
                self._basic_commands["vrf"].extend(commands)
                commands.clear()

    def config_routing_policy(self) -> None:
        self.__routing_commands["route-policy"].extend([
            "route-policy PASS",
            "pass",
            "end-policy"
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
            # Iterate through each area number
            for area_number in self.get_all_areas():
                # Iterate through each area number
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

        if any(cmd_list for cmd_list in self.__bgp_commands.values()):
            if self.ios_xr:
                keys = ["start", "id", "address_families", "neighbor_group", "ipv4_unicast",
                        "vpn_v4", "neighbor", "ebgp"]

                self.__bgp_commands["vpn_v4"].append("exit")  # To exit out of the neighbor-group command

            else:
                keys = ["start", "id", "neighbor", "vpn_v4", "ebgp"]

            for key in keys:
                if self.__bgp_commands[key]:
                    self.__routing_commands["bgp"].extend(self.__bgp_commands[key])
                    self.__bgp_commands[key].clear()

            self.__routing_commands["bgp"].append("exit")

    def is_provider_edge(self) -> bool:
        return any(interface.egp for interface in self.all_phys_interfaces())

    def bgp_routing_config(self, initialization: bool = False, new_neighbor_ids: list[str] = None) -> None:

        if new_neighbor_ids is None:
            new_neighbor_ids = []

        # Step 1: Error/warning check
        def error_check():
            if self.as_number == 0:
                raise ValueError("The AS number for this router hasn't been assigned yet.")

            if not self.ibgp_adjacent_router_ids:
                raise ValueError("No adjacent routers are assigned. Please assign a route reflector first.")

            if not (self.route_reflector or self.is_provider_edge()):
                raise NetworkError("This router is neither a route-reflector, "
                                   "nor a provider edge, so it's not for BGP routing")

            if (not self.__any_mpls_interfaces()) and self.vrfs:
                print_warning(
                    "VRF is configured without any MPLS capabilities. MPLS is required for the VPN connection "
                    "to be established.")

        # Step 2: Starting with the AS number and the ID
        def open_config():
            self.__bgp_commands["start"] = [f"router bgp {self.as_number}"]

        def define_router_id():
            self.__bgp_commands["id"] = [
                f"bgp router-id {self.id()}",
            ]

            if self.route_reflector:
                self.__bgp_commands["id"].append(f"bgp cluster-id {self.id()}")

        # Step 3: Initialize address families
        def address_families():
            if self.ios_xr:
                # IPv4 Unicast
                self.__bgp_commands["address_families"] = [
                    "address-family ipv4 unicast",
                    "exit"
                ]

                if self.__any_mpls_interfaces():
                    # VPNv4 Unicast
                    self.__bgp_commands["address_families"].extend([
                        "address-family vpnv4 unicast",
                        "exit"
                    ])

                    # Goes inside the neighbor-group configuration
                    self.__bgp_commands["ipv4_unicast"] = ["address-family ipv4 labeled-unicast"]
                    self.__bgp_commands["vpn_v4"] = ["address-family vpnv4 unicast"]

                else:
                    self.__bgp_commands["ipv4_unicast"] = ["address-family ipv4 unicast"]

            else:
                if self.__any_mpls_interfaces():
                    self.__bgp_commands["vpn_v4"] = ["address-family vpnv4"]

                    for rtr_id in new_neighbor_ids:
                        self.__bgp_commands["vpn_v4"].extend([
                            f"neighbor {rtr_id} activate",
                            f"neighbor {rtr_id} send-community both"
                        ])

                        self.__bgp_commands["vpn_v4"].append(f"neighbor {rtr_id} route-reflector-client")
                    self.__bgp_commands["vpn_v4"].append("exit-address-family")

        # Step 4: Configure neighbor-group
        def xr_neighbor_group():
            if self.ios_xr:
                neighbor_group_name = "UNTITLED"
                neighbor_config_cmd = "!"

                # Route-reflector or provider edge?
                if self.route_reflector:
                    neighbor_group_name = "RR_TO_CLIENT"
                    neighbor_config_cmd = "route-reflector-client"

                elif self.is_provider_edge():
                    neighbor_group_name = "CLIENT_TO_RR"
                    neighbor_config_cmd = "soft-reconfiguration inbound always"

                # Introduce neighbor-group
                self.__bgp_commands["neighbor_group"] = [
                    f"neighbor-group {neighbor_group_name}",
                    f"remote-as {self.as_number}",
                    f"update-source {self.loopback(0)}"
                ]

                # Insert the commands
                self.__bgp_commands["ipv4_unicast"].extend([neighbor_config_cmd, "exit"])
                if self.__any_mpls_interfaces():
                    self.__bgp_commands["vpn_v4"].extend([neighbor_config_cmd, "exit"])

                return neighbor_group_name

            else:
                return None

        # Step 5: Assign neighbors
        def assign_neighbors():
            # Assign neighbor group to each adjacent routers to establish neighbor
            neighbor_group_name = xr_neighbor_group()

            for rtr_id in new_neighbor_ids:
                if self.ios_xr:
                    self.__bgp_commands["neighbor"].extend([
                        f"neighbor {rtr_id}",
                        f"use neighbor-group {neighbor_group_name}",
                        "exit"
                    ])

                else:
                    self.__bgp_commands["neighbor"].extend([
                        f"neighbor {rtr_id} remote-as {self.as_number}",
                        f"neighbor {rtr_id} update-source {self.loopback(0)}",
                    ])

                    if self.route_reflector:
                        self.__bgp_commands["neighbor"].append(f"neighbor {rtr_id} route-reflector-client")

        # Step 6: EBGP Redistribution
        def redistribution_to_egp():

            vrfs = [(rd, vrf_[VRFKey.NAME]) for rd, vrf_ in self.vrfs.items()]

            # Helper Functions
            def establish_neighbors():
                for interface in filter(lambda i: i.vrf_name == vrf_name and not i.static_routing,
                                        self.all_phys_interfaces()):

                    if not isinstance(interface.remote_device, Router):
                        raise TypeError(f"This remote device '{str(interface.remote_device)}' is not a router")

                    remote_as = interface.remote_device.as_number
                    interface_ip = interface.remote_device.interface(interface.remote_port).ip_address

                    self.config_routing_policy()  # To allow all the prefixes in

                    if self.ios_xr:
                        self.__bgp_commands["ebgp"].extend([
                            f"neighbor {interface_ip}",
                            f"remote-as {remote_as}",
                            "address-family ipv4 unicast",
                            "route-policy PASS in",
                            "route-policy PASS out",
                            "soft-reconfiguration inbound always"
                        ])

                    else:
                        self.__bgp_commands["ebgp"].extend([
                            f"neighbor {interface_ip} remote-as {remote_as}",
                            f"neighbor {interface_ip} activate"
                        ])

            def redistribute_in_vrf(name, rd):
                if self.ios_xr:
                    self.__bgp_commands["ebgp"] = [
                        f"vrf {name}",
                        f"rd {self.as_number}:{rd}",
                        "address-family ipv4 unicast",
                        "label mode per-vrf",
                        "redistribute connected",
                        "exit"
                    ]
                else:
                    self.__bgp_commands["ebgp"] = [
                        f"address-family ipv4 vrf {vrf_name}",
                        "redistribute connected"
                    ]

            # Iterate through each VRF
            for rd, vrf_name in vrfs:

                # Open the VRF configuration section and redistribute the IGP
                redistribute_in_vrf(vrf_name, rd)

                # Establish neighborhood adjacency for each remote interfaces
                establish_neighbors()

                if self.ios_xr:
                    self.__bgp_commands["ebgp"].append("exit")
                else:
                    self.__bgp_commands["ebgp"].append("exit-address-family")

            # No VRFs configured?
            if not vrfs:
                if self.ios_xr:
                    self.__bgp_commands["address_families"].insert(1, "redistribute connected")
                else:
                    self.__bgp_commands["ebgp"].append("redistribute connected")

                establish_neighbors()

        def execute_all():
            error_check()
            open_config()
            if initialization:
                define_router_id()
                address_families()
            if new_neighbor_ids:
                assign_neighbors()
            redistribution_to_egp()

        execute_all()

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

    def send_script(self, print_to_console: bool = True) -> None:
        print_log("Building configuration...")

        # Start with 'configure terminal'
        script = ["configure terminal"]

        # # Generate a script for any MPLS routing
        # self.__generate_mpls_command()

        # Transfer all the VRF commands to a single list
        self.__consolidate_vrf_commands()

        # Transfer all the BGP commands to a single list
        self.__consolidate_bgp_commands()

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
            script.extend(self.__routing_commands[attr])
            self.__routing_commands[attr].clear()

        if self.ios_xr:
            script.append("commit")

        script.append("end")

        if print_to_console:
            NetworkDevice.print_script(script, Fore.YELLOW)
