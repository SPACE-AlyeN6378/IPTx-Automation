from colorama import Fore

from components.devices.network_device import NetworkDevice
from components.devices.router.virtual_route_forwarding import VRF
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List, Set

from iptx_utils import print_warning, print_log, print_denied, DeviceError, NetworkError


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
        self.vrfs: set[VRF] = set()

        # MPLS
        self.__mpls_configured: bool = False

        # Cisco commands
        self._starter_commands.update({
            "vrf": []
        })
        self._routing_commands: Dict[str, List[str]] = {
            "route-policy": [],
            "client-connection": [],
            "ospf": [],
            "bgp": [],
            "mpls": []
        }
        self._bgp_commands: dict[str, list[str]] = {
            "start": [],
            "id": [],
            "neighbor": [],
            "af_vpn_v4": [],
            "external": [],
            "close": []
        }

    def __str__(self):
        name = super().__str__().replace("Device", "Router")
        return name

    def _any_mpls_interfaces(self) -> bool:
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

    def add_vrf(self, new_vrf: VRF) -> None:
        # ERROR CHECK =============================
        if not self.is_provider_edge():
            raise DeviceError("This is not a provider edge router, so VRF cannot be configured in this device")

        if self.as_number == 0:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        if new_vrf.name in [vrf.name for vrf in self.vrfs]:
            raise ValueError(f"VRF with name {new_vrf.name} already exists")
        # =========================================

        self.vrfs.add(new_vrf)

    def get_vrf(self, name: str = None, port: str = None) -> VRF | None:
        if port:
            name = self.interface(port).vrf_name

        for vrf in self.vrfs:
            if vrf.name == name:
                return vrf

        return None

    def _consolidate_vrf_setup_commands(self) -> None:
        self._starter_commands["vrf"].clear()
        for vrf in self.vrfs:
            self._starter_commands["vrf"].extend(vrf.get_setup_cmd())

    def set_as_route_reflector(self) -> None:
        self.route_reflector = True
        self.set_hostname(self.hostname + "-RR")

    def not_route_reflector(self) -> None:
        self.route_reflector = False
        if self.hostname.endswith("-RR"):
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
        self._routing_commands["ospf"] = [
            f"router ospf {self.OSPF_PROCESS_ID}",  # Define the process ID
            f"router-id {self.id()}",  # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # All the EGP interfaces and loopbacks are configured as passive, in the OSPF section
        for interface in self.all_interfaces():
            if not interface.ospf_allow_hellos:
                self._routing_commands["ospf"].append(f"passive-interface {str(interface)}")

        if self._any_mpls_interfaces():
            self._routing_commands["ospf"].append("mpls ldp sync")

        self._routing_commands["ospf"].append("exit")

    def is_provider_edge(self) -> bool:
        return any(interface.egp for interface in self.all_phys_interfaces())

    def bgp_routing(self, initialization: bool = False, ibgp_neighbor_ids: Iterable[str] = None,
                    redistribution_to_egp: bool = False) -> None:

        if ibgp_neighbor_ids is None:
            ibgp_neighbor_ids = []

        # Step 1: Error/warning check
        def error_check():
            if self.as_number == 0:
                raise ValueError("The AS number for this router hasn't been assigned yet.")

            if not (self.route_reflector or self.is_provider_edge()):
                raise NetworkError("This router is neither a route-reflector, "
                                   "nor a provider edge, so it's not for BGP routing")

            if (not self._any_mpls_interfaces()) and self.vrfs:
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
            if self._any_mpls_interfaces():
                self._bgp_commands["af_vpn_v4"] = ["address-family vpnv4", "exit-address-family"]

        # Step 4: Assign neighbors
        def assign_ibgp_neighbors():
            # Assign neighbor group to each adjacent routers to establish neighbor
            for rtr_id in ibgp_neighbor_ids:
                if rtr_id not in self.ibgp_adjacent_router_ids:
                    self.ibgp_adjacent_router_ids.add(rtr_id)

                    self._bgp_commands["neighbor"].extend([
                        f"neighbor {rtr_id} remote-as {self.as_number}",
                        f"neighbor {rtr_id} update-source {self.loopback(0)}",
                    ])

                    if self._any_mpls_interfaces():
                        if not self._bgp_commands["af_vpn_v4"]:
                            address_families()

                        self._bgp_commands["af_vpn_v4"][-1:-1] = [
                            f"neighbor {rtr_id} activate",
                            f"neighbor {rtr_id} send-community both"
                        ]

                    if self.route_reflector:
                        self._bgp_commands["neighbor"].append(f"neighbor {rtr_id} route-reflector-client")
                        self._bgp_commands["af_vpn_v4"].insert(-1, f"neighbor {rtr_id} route-reflector-client")

        # Step 6: EBGP Redistribution
        def redistribution_to_external_routes():

            # Iterate through each VRF
            for vrf in self.vrfs:
                # Establish neighborhood adjacency for each remote interfaces
                af_commands = vrf.generate_af_command(self.id())
                print(type(af_commands))
                self._bgp_commands["external"].extend(af_commands)

        def close_out():
            self._bgp_commands["close"] = ["exit"]

        def execute_function():
            error_check()
            open_config()
            if initialization:
                define_router_id()
                address_families()
            if ibgp_neighbor_ids:
                assign_ibgp_neighbors()
            if redistribution_to_egp:
                redistribution_to_external_routes()
            close_out()

        execute_function()

    def bgp_disable(self):
        if self.ibgp_adjacent_router_ids:
            self._bgp_commands["start"].insert(0, f"no router bgp {self.as_number}")
            self.ibgp_adjacent_router_ids.clear()

        else:
            print_denied("The BGP routing is not yet initialized")

    def __mpls_ldp_activate(self) -> None:
        """
        If MPLS is enabled in any interfaces, enable LDP synchronization
        :return:
        """
        if self._any_mpls_interfaces() and not self.__mpls_configured:
            self._routing_commands["mpls"] = [
                "mpls ldp router-id Loopback0",
                "mpls label protocol ldp"
            ]

            self.__mpls_configured = True

    def client_connection_routing(self, interface_port: str) -> None:
        chosen_interface = self.interface(interface_port)
        if not chosen_interface.egp:
            raise NetworkError("This is not an inter-autonomous connection")

        remote_device: Router = chosen_interface.remote_device
        remote_port: str = chosen_interface.remote_port
        remote_int_ip_address = remote_device.interface(remote_port).ip_address

        if chosen_interface.static_routing:
            self._routing_commands["client-connection"] = [f"ip route 0.0.0.0 0.0.0.0 {remote_int_ip_address}"]

        else:
            remote_as = remote_device.as_number

            if not self._routing_commands["client-connection"]:
                self._routing_commands["client-connection"] = [
                    f"router bgp {self.as_number}",
                    f"bgp router-id {self.id()}",
                    f"network {self.id()} mask 255.255.255.255",
                    "exit"
                ]
            self._routing_commands["client-connection"].insert(-1, f"neighbor {remote_int_ip_address} "
                                                                   f"remote-as {remote_as}")

    def generate_script(self) -> List[str]:
        print_log(f"Building configuration for {str(self)}...")

        # Start with an empty list
        script = []

        # # Generate a script for any MPLS routing
        self.__mpls_ldp_activate()

        # Transfer all the VRF commands to a single list
        self._consolidate_vrf_setup_commands()

        # Transfer all the BGP commands to a single list
        for commands in self._bgp_commands.values():
            self._routing_commands["bgp"].extend(commands)
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
        for attr in self._routing_commands.keys():
            script.extend(self._routing_commands[attr])
            self._routing_commands[attr].clear()

        script.append("write memory")
        return script
