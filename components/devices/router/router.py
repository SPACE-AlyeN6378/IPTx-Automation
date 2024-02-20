from colorama import Fore

from components.devices.network_device import NetworkDevice
from components.interfaces.physical_interfaces.router_interface import RouterInterface
from components.interfaces.loopback.loopback import Loopback
from typing import Iterable, Dict, List, Set


class Router(NetworkDevice):

    def __init__(self, router_id: str, hostname: str = "Router",
                 interfaces: Iterable[RouterInterface | Loopback] = None, ios_xr: bool = False) -> None:

        self.OSPF_PROCESS_ID = 65000
        self.OSPF_MPLS_PROCESS_ID = 2500

        self.ios_xr: bool = ios_xr
        self.priority = 20  # Priority on a scale of 1 to 100

        super().__init__(device_id=router_id, hostname=hostname)
        self.add_interface(Loopback(cidr=router_id, description=f"LOOPBACK-FHL-{hostname}"))
        self.add_interface(*interfaces)

        self.reference_bw = self.get_max_bandwidth() // 1000

        self.__routing_commands: Dict[str, List[str]] = {
            "ospf": [],
            "ospf_mpls": [],
            "bgp": []
        }

    # ********* GETTERS *********
    # Overriden from NetworkDevice for changing type alias
    def interface(self, port: str) -> RouterInterface:
        return super().interface(port)

    # Overriden from NetworkDevice for changing type alias
    def interface_range(self, *ports: str) -> List[RouterInterface]:
        return super().interface_range(*ports)

    # Overriden from NetworkDevice for changing type alias
    def all_phys_interfaces(self) -> List[RouterInterface]:
        return super().all_phys_interfaces()

    # Overriden from NetworkDevice for changing type alias
    def all_interfaces(self) -> List[RouterInterface | Loopback]:
        return super().all_interfaces()

    # Overriden from NetworkDevice
    def add_interface(self, *new_interfaces: RouterInterface | Loopback) -> None:
        if not all(isinstance(interface, (RouterInterface, Loopback)) for interface in new_interfaces):
            raise TypeError("All interfaces should either be a RouterInterface or a Loopback")

        if self.ios_xr:
            for interface in new_interfaces:
                interface.__xr_mode = True

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
    def initialize_route(self):
        # Configure OSPF for all routers
        for interface in self.all_interfaces():
            if isinstance(interface.remote_device, Router):
                interface.ospf_config(self.OSPF_PROCESS_ID)

        # Generate Cisco command
        self.__routing_commands["ospf"] = [
            f"router ospf {self.OSPF_PROCESS_ID}",  # Define the process ID
            f"router-id {self.loopback(0).ip_address}",  # Router ID
            f"auto-cost reference-bandwidth {self.reference_bw}",  # Cost is autoconfigured using reference BW
        ]

        # Generate Cisco command
        if self.ios_xr:
            for area_number in self.get_all_areas():
                self.__routing_commands["ospf"].append(f"area {area_number}")

                for interface in self.get_ints_by_ospf_area(area_number):
                    self.__routing_commands["ospf"].extend(interface.generate_ospf_xr_commands())

                self.__routing_commands["ospf"].append("exit")

        else:  # For IOS routers, all the EGP interfaces and the first loopback are configured as passive
            for interface in self.all_phys_interfaces():
                if interface.egp:
                    self.__routing_commands["ospf"].append(f"passive-interface {str(interface)}")

            for interface in self.all_loopbacks():
                if not interface.allow_hellos:
                    self.__routing_commands["ospf"].append(f"passive-interface {str(interface)}")

        self.__routing_commands["ospf"].append("exit")

    # Generate a complete configuration script
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
        NetworkDevice.print_script(script, Fore.CYAN)
