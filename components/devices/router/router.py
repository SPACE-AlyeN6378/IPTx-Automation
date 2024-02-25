from colorama import Fore

from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List, Set


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

        self.reference_bw = self.get_max_bandwidth() // 1000

        self.__routing_commands: Dict[str, List[str] | Dict[str, List[str]]] = {
            "ospf": [],
            "bgp": {
                "start": [],
                "id": [],
                "address_families": [],
                "ipv4_uni-cast": [],
                "vpn_v4": [],
                "neighbor_group": [],
                "neighbor": [],
            }
        }

    def __str__(self):
        name = super().__str__().replace("Device", "Router")
        if self.ios_xr:
            name = "XR " + name

        return name

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

    # ********* SETTERS *********
    # Shortcut to setting up the OSPF area numbers for each router interface
    def set_ospf_area(self, area_number, ports: List[str] | str) -> None:

        if isinstance(ports, str):
            self.interface(ports).ospf_area = area_number

        else:
            for interface in self.interface_range(*ports):
                interface.ospf_area = area_number

    # Basic Route initialization
    def begin_internal_routing(self):
        # Configure OSPF for all interfaces
        for interface in self.all_phys_interfaces():
            # The interface should be connected to another router, and within autonomous system
            if isinstance(interface.remote_device, Router):
                if not interface.egp:
                    interface.ospf_config(process_id=self.OSPF_PROCESS_ID, p2p=interface.ospf_p2p)

                # If the interface is for inter-autonomous routing, prevent OSPF adjacency using passive-interface
                else:
                    interface.ospf_passive_enable()

        for interface in self.all_loopbacks():
            interface.ospf_config(process_id=self.OSPF_PROCESS_ID)

        # Generate Cisco command for during router OSPF configuration
        self.__routing_commands["ospf"] = [
            f"router ospf {self.OSPF_PROCESS_ID}",  # Define the process ID
            f"router-id {self.id()}",  # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # Generate Cisco command for IOS XR
        if self.ios_xr:
            for area_number in self.get_all_areas():
                self.__routing_commands["ospf"].append(f"area {area_number}")

                for interface in self.get_ints_by_ospf_area(area_number):
                    # If the physical interface is connected or is just a loopback
                    if interface.int_type == "Loopback":
                        self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())
                    elif interface.remote_device is not None:
                        self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())

                self.__routing_commands["ospf"].append("exit")

        else:  # For IOS routers, all the EGP interfaces and loopbacks are configured as passive, in the OSPF section
            for interface in self.all_interfaces():
                if not interface.ospf_allow_hellos and interface is not None:
                    self.__routing_commands["ospf"].append(f"passive-interface {str(interface)}")

        self.__routing_commands["ospf"].append("exit")

    def begin_ibgp_routing(self) -> None:
        # Error check
        if self.as_number == 0:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        if not self.ibgp_adjacent_router_ids:
            raise ValueError("The AS number for this router hasn't been assigned yet.")

        # Starting with the AS number and the ID
        self.__routing_commands["bgp"]["start"] = [f"router bgp {self.as_number}"]
        self.__routing_commands["bgp"]["id"] = [
            f"bgp router-id {self.id()}",
            f"bgp cluster-id {self.id()}"
        ]

        # VPNv4 Routing
        if self.ios_xr:
            pass
        else:
            # VPNv4 Routing
            self.__routing_commands["bgp"]["vpn_v4"] = ["address-family vpnv4"]

            for router_id in self.ibgp_adjacent_router_ids:
                self.__routing_commands["bgp"]["neighbor"].extend([
                    f"neighbor {router_id} remote-as {self.as_number}",
                    f"neighbor {router_id} send-community extended"
                ])

                self.__routing_commands["bgp"]["vpn_v4"].extend([
                    f"neighbor {router_id} activate",
                    f"neighbor {router_id} send-community extended"
                ])

            self.__routing_commands["bgp"]["vpn_v4"].append("exit-address-family")

    def send_script(self) -> None:
        # Start with 'configure terminal'
        script = ["configure terminal"]

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
        NetworkDevice.print_script(script, Fore.WHITE)
