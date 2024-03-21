from colorama import Fore

from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List, Set
from enum import Enum

from iptx_utils import print_warning, print_log, print_denied, DeviceError, NetworkError


class VRFKey(Enum):
    NAME = 'name',
    IMPORT = 'import',
    INTERFACES = 'interfaces'


class Router(NetworkDevice):

    def __init__(self, router_id: str, hostname: str = "Router",
                 interfaces: Iterable[RouterInterface | Loopback] = None) -> None:

        self.OSPF_PROCESS_ID: int = 65000
        self.priority: int = 20  # Priority on a scale of 1 to 100

        # BGP properties and attributes
        self.as_number: int = 0
        self.route_reflector: bool = False
        self.ibgp_adjacent_router_ids: set[str] = set()

        super().__init__(device_id=router_id, hostname=hostname)
        self.add_interface(Loopback(cidr=router_id, description=f"LOOPBACK-FHL-{hostname}"))
        self.add_interface(*interfaces)

        # Reference bandwidth
        self.reference_bw = self.get_max_bandwidth() // 1000

        # VRF
        self.vrfs: dict[int, dict[VRFKey, str | set[int | RouterInterface]]] = dict()

        # MPLS
        self.__mpls_configured: bool = False

        self._vrf_commands: dict[int, list[str]] = dict()
        self._starter_commands.update({
            "vrf_af_disable": [],
            "vrf": []
        })

        self.__routing_commands: Dict[str, List[str]] = {
            "route-policy": [],
            "ospf": [],
            "bgp": [],
            "mpls": []
        }

        self._bgp_commands: dict[str, list[str]] = {
            "start": [],
            "id": [],
            "neighbor": [],
            "af_vpn_v4": [],
            "external": []
        }

    def __str__(self):
        name = super().__str__().replace("Device", "Router")
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
        if not self.is_provider_edge:
            raise DeviceError("This is not a provider edge router, so VRF cannot be configured in this device")

        if self.as_number == 0:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        if rd_number in self.vrfs:
            raise ValueError(f"VRF with name RD {rd_number} already exists")

        self.vrfs[rd_number] = {VRFKey.NAME: name, VRFKey.IMPORT: set(), VRFKey.INTERFACES: set()}
        self._vrf_commands[rd_number] = [
            f"vrf definition {name}",
            f"rd {self.as_number}:{rd_number}",
            "address-family ipv4",
            f"route-target export {self.as_number}:{rd_number}",
            "exit",
            "exit",
        ]

    def add_route_targets(self, rd_number: int, new_rts: Iterable[int]) -> None:
        self.vrfs[rd_number][VRFKey.IMPORT] |= set(new_rts)

        if not self._vrf_commands[rd_number]:
            self._vrf_commands[rd_number] = [
                f"vrf definition {self.vrfs[rd_number][VRFKey.NAME]}",
                "address-family ipv4",
                "exit",
                "exit"
            ]

        for rt in new_rts:
            self._vrf_commands[rd_number].insert(-2, f"route-target import {self.as_number}:{rt}")

    def del_route_target(self, rd_number: int, rt_to_be_removed: int) -> None:
        self.vrfs[rd_number][VRFKey.IMPORT].discard(rt_to_be_removed)

        if not self._vrf_commands[rd_number]:
            self._vrf_commands[rd_number] = [
                f"vrf definition {self.vrfs[rd_number][VRFKey.NAME]}",
                "address-family ipv4",
                "exit",
                "exit"
            ]

        self._vrf_commands[rd_number].insert(-2, f"no route-target import {self.as_number}:{rt_to_be_removed}")

        if self.ibgp_adjacent_router_ids:   # If BGP is configured in the router
            # Reset the VRF configuration
            self.disable_vrf_redistribution(self.vrfs[rd_number][VRFKey.NAME])
            self.bgp_routing(redistribution=True)

    def assign_int_to_vrf(self, rd_number: int, designated_port: str) -> None:
        self.interface(designated_port) \
         .assign_vrf(self.vrfs[rd_number][VRFKey.NAME])

        self.vrfs[rd_number][VRFKey.INTERFACES].add(self.interface(designated_port))

    def remove_vrf(self, rd_number: int) -> None:
        # Reconfigure IP Addresses for each interface
        for interface in self.vrfs[rd_number][VRFKey.INTERFACES]:
            interface.remove_vrf()

        # Remove the VRF
        removed_vrf = self.vrfs.pop(rd_number)

        # Generate the command
        self._vrf_commands[rd_number] = [f"no vrf definition {removed_vrf[VRFKey.NAME]}"]

    def set_as_route_reflector(self) -> None:
        self.route_reflector = True
        self.set_hostname(self.hostname + "-RR")

    def not_route_reflector(self) -> None:
        self.route_reflector = False
        self.set_hostname(self.hostname.replace("-RR", ""))

    def begin_internal_routing(self) -> None:
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
            f"router-id {self.id()}", # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # All the EGP interfaces and loopbacks are configured as passive, in the OSPF section
        for interface in self.all_interfaces():
            if not interface.ospf_allow_hellos:
                self.__routing_commands["ospf"].append(f"passive-interface {str(interface)}")

        if self.__any_mpls_interfaces():
            self.__routing_commands["ospf"].append("mpls ldp sync")

        self.__routing_commands["ospf"].append("exit")

    def is_provider_edge(self) -> bool:
        return any(interface.egp for interface in self.all_phys_interfaces())

    def bgp_routing(self, initialization: bool = False, ibgp_neighbor_ids: Iterable[str] = None,
                    redistribution: bool = False) -> None:

        if ibgp_neighbor_ids is None:
            ibgp_neighbor_ids = []

        # Step 1: Error/warning check
        def error_check():
            if self.as_number == 0:
                raise ValueError("The AS number for this router hasn't been assigned yet.")

            if not (self.route_reflector or self.is_provider_edge()):
                raise NetworkError("This router is neither a route-reflector, "
                                   "nor a provider edge, so it's not for BGP routing")

            if not (initialization or ibgp_neighbor_ids or redistribution):
                raise TypeError("What should I configure?")

            if (not self.__any_mpls_interfaces()) and self.vrfs:
                print_warning(
                    "VRF is configured without any MPLS capabilities. MPLS is required for the VPN connection "
                    "to be established.")

        # Step 2: Starting with the AS number and the ID
        def open_config():
            self._bgp_commands["start"] = [f"router bgp {self.as_number}"]

        def define_router_id():
            self._bgp_commands["id"] = [
                f"bgp router-id {self.id()}",
            ]

            if self.route_reflector:
                self._bgp_commands["id"].append(f"bgp cluster-id {self.id()}")

        # Step 3: Initialize address families
        def address_families():
            if self.__any_mpls_interfaces():
                self._bgp_commands["af_vpn_v4"] = ["address-family vpnv4", "exit-address-family"]

        # Step 4: Assign neighbors
        def assign_ibgp_neighbors():
            # Assign neighbor group to each adjacent routers to establish neighbor
            for rtr_id in ibgp_neighbor_ids:
                self.ibgp_adjacent_router_ids.add(rtr_id)

                self._bgp_commands["neighbor"].extend([
                    f"neighbor {rtr_id} remote-as {self.as_number}",
                    f"neighbor {rtr_id} update-source {self.loopback(0)}",
                ])

                self._bgp_commands["af_vpn_v4"][-1:-1] = [
                    f"neighbor {rtr_id} activate",
                    f"neighbor {rtr_id} send-community both"
                ]

                if self.route_reflector:
                    self._bgp_commands["neighbor"].append(f"neighbor {rtr_id} route-reflector-client")
                    self._bgp_commands["af_vpn_v4"].insert(-1, f"neighbor {rtr_id} route-reflector-client")

        # Step 6: EBGP Redistribution
        def redistribution_to_external_routes():
            vrfs = [(rd, vrf_[VRFKey.NAME]) for rd, vrf_ in self.vrfs.items()]

            # Helper Functions
            def establish_ebgp_neighbors(vrf_name=None):
                for interface in filter(lambda i: i.vrf_name == vrf_name and not i.static_routing,
                                        self.all_phys_interfaces()):

                    if not isinstance(interface.remote_device, Router):
                        raise TypeError(f"This remote device '{str(interface.remote_device)}' is not a router")

                    remote_as = interface.remote_device.as_number
                    interface_ip = interface.remote_device.interface(interface.remote_port).ip_address

                    self._bgp_commands["external"].append(f"neighbor {interface_ip} remote-as {remote_as}")
                    if vrf_name is not None:
                        self._bgp_commands["external"].append(f"neighbor {interface_ip} activate")

            # Iterate through each VRF
            for rd, name in vrfs:

                # Open the VRF configuration section and redistribute the IGP
                self._bgp_commands["external"] = [
                    f"address-family ipv4 vrf {name}",
                    "redistribute connected"
                ]

                # Establish neighborhood adjacency for each remote interfaces
                establish_ebgp_neighbors(name)
                
                # Exit out
                self._bgp_commands["external"].append("exit-address-family")

            # No VRFs configured?
            if not vrfs:
                self._bgp_commands["external"].append("redistribute connected")
                establish_ebgp_neighbors()

        def execute_function():
            error_check()
            open_config()
            if initialization:
                define_router_id()
                address_families()
            if ibgp_neighbor_ids:
                assign_ibgp_neighbors()
            if redistribution:
                redistribution_to_external_routes()

        execute_function()

    def bgp_reset(self):
        if self.ibgp_adjacent_router_ids:
            self.bgp_routing(initialization=True, ibgp_neighbor_ids=self.ibgp_adjacent_router_ids)
            self._bgp_commands["start"].insert(0, f"no router bgp {self.as_number}")

        else:
            print_denied("The BGP routing is not yet initialized")

    def disable_vrf_redistribution(self, vrf_name: str) -> None:
        """
        Disables the VRF destribution, only used when changing/updating the route targets
        :param vrf_name: 
        :return: 
        """
        if not self._starter_commands["vrf_af_disable"]:
            self._starter_commands["vrf_af_disable"] = [
                f"router bgp {self.as_number}",
                "exit"
            ]

        else:
            self._starter_commands["vrf_af_disable"].insert(-1, f"no address-family ipv4 vrf {vrf_name}")

    def __mpls_ldp_activate(self) -> None:
        """
        If MPLS is enabled in any interfaces, enable LDP synchronization
        :return:
        """
        if self.__any_mpls_interfaces() and not self.__mpls_configured:
            self.__routing_commands["mpls"] = [
                "mpls ldp router-id Loopback0",
                "mpls label protocol ldp"
            ]

            self.__mpls_configured = True

    def send_script(self, print_to_console: bool = True) -> List[str]:
        print_log("Building configuration...")

        # Start with 'configure terminal'
        script = ["configure terminal"]

        # # Generate a script for any MPLS routing
        self.__mpls_ldp_activate()

        # Transfer all the VRF commands to a single list
        for commands in self._vrf_commands.values():
            self._starter_commands["vrf"].extend(commands)
            commands.clear()

        # Transfer all the BGP commands to a single list
        for commands in self._bgp_commands.values():
            self.__routing_commands["bgp"].extend(commands)
            commands.clear()

        # Iterate through each cisco command by key
        for attr in self._starter_commands.keys():
            # Add the cisco commands to the script and clear it, so that it doesn't have to be
            # added again, until any of the attributes have changed
            script.extend(self._starter_commands[attr])
            self._starter_commands[attr].clear()

        # Iterate through each interface
        for interface in self.all_interfaces():
            script.extend(interface.generate_command_block())

        # Iterate through each routing command
        for attr in self.__routing_commands.keys():
            script.extend(self.__routing_commands[attr])
            self.__routing_commands[attr].clear()

        script.append("end")

        if print_to_console:
            NetworkDevice.print_script(script, Fore.YELLOW)

        return script
