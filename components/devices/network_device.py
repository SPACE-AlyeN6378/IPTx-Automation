from __future__ import annotations

from typing import List, Iterable, Any


from iptx_utils import NetworkError
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface
from components.interfaces.loopback.loopback import Loopback
from iptx_utils import NotFoundError, smallest_missing_non_negative_integer, CommandsDict
from colorama import Style, Fore
import re


# import pyperclip


class NetworkDevice:
    # Regex for hostname validation
    hostname_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    hostname_regex = re.compile(hostname_pattern)

    # Print out the script
    @staticmethod
    def print_script(commands: Iterable[str], color=Fore.WHITE):

        indent_size = 0
        for command_line in commands:

            indent = '  ' * indent_size

            if command_line == "exit" or command_line == "exit-address-family":
                print(f"{color}{indent}!{Style.RESET_ALL}")
                indent_size -= 1
            else:
                print(f"{color}{indent}{command_line}{Style.RESET_ALL}")

            if "hostname" in command_line:
                print(f'{color}!{Style.RESET_ALL}')

            if (command_line[:9] == "interface" or
                    command_line[:7] == "router " or
                    command_line[:5] == "area " or
                    command_line[:14] == "address-family" or
                    command_line[:14] == "neighbor-group" or
                    command_line[:3] == "vrf"):

                print(f"{Fore.RED}BEEP{Style.RESET_ALL}")
                indent_size += 1



    # Constructor
    def __init__(self, device_id: str = None, hostname: str = "NetworkDevice",
                 interfaces: Iterable[PhysicalInterface] = None) -> None:

        # Hostname validation
        if not NetworkDevice.hostname_regex.match(hostname):
            raise ValueError(f"ERROR: '{hostname}' is not a valid hostname")

        # If the interface is not given
        if interfaces is None:
            interfaces = []

        # Attributes
        self.__device_id: str = device_id
        self.hostname: str = hostname
        self.__phys_interfaces: List[PhysicalInterface] = []
        self.__loopbacks: List[Loopback] = []
        self.add_interface(*interfaces)

        # Cisco commands
        self._basic_commands: CommandsDict = {
            "timezone": ["clock timezone Dhaka 6 0"],
            "hostname": [f"hostname {self.hostname}"]
        }

    # Stringify
    def __str__(self):
        return f"Device '{self.hostname}'"

    # The equal and hashable operator are for identification
    def __eq__(self, other):
        if isinstance(other, NetworkDevice):
            return self.__device_id == other.__device_id

    def __hash__(self):
        return hash(self.__device_id)

    # Getters ---------------------------------------------------------------
    def id(self):
        return self.__device_id

    def interface(self, port: str) -> Any:
        for interface in self.__phys_interfaces:
            if port == interface.port:
                return interface

        # Raise an error if it doesn't exist
        raise NotFoundError(f"ERROR in {str(self)}: Interface with port {port} is not included in "
                            f"this network device")

    def interface_range(self, *ports: str) -> List[Any]:
        if len(ports) > len(set(ports)):
            raise IndexError("All the interface ports need to be unique")

        return [self.interface(port) for port in ports]

    def loopback(self, loopback_id: int) -> Loopback:
        for interface in self.__loopbacks:
            if loopback_id == interface.port:
                return interface

        # Raise an error if it doesn't exist
        raise NotFoundError(f"ERROR in {self.hostname}: Loopbacks with ID {loopback_id} is not included in "
                            f"this network device")

    def all_phys_interfaces(self) -> List[Any]:
        return self.__phys_interfaces

    def all_loopbacks(self) -> List[Loopback]:
        return self.__loopbacks

    def all_interfaces(self) -> List[Any]:
        return self.__phys_interfaces + self.__loopbacks

    def get_max_bandwidth(self) -> int:
        return max(interface.bandwidth for interface in self.all_phys_interfaces())

    def remote_device(self, port) -> NetworkDevice:
        device = self.interface(port).remote_device
        if device is None:
            print(
                f"{Fore.YELLOW}WARNING: Unconnected '{self.interface(port)}', so no remote device{Style.RESET_ALL}")

        return device

    def remote_port(self, port) -> str:
        port_ = self.interface(port).remote_port
        if port_ is None:
            print(
                f"{Fore.YELLOW}WARNING: Unconnected '{self.interface(port)}', so no remote device{Style.RESET_ALL}")

        return port_

    # -----------------------------------------------------------------------

    # *** Setters and modifiers ***
    # Changes/updates the ID
    def update_id(self, new_id: int | str) -> None:
        self.__device_id = new_id

    # Changes the hostname
    def set_hostname(self, new_hostname: str):

        if not NetworkDevice.hostname_regex.match(new_hostname):
            raise ValueError(f"ERROR: '{new_hostname}' is not a valid hostname")

        self.hostname = new_hostname

        # Update the dictionary of cisco commands
        self._basic_commands["hostname"] = [f"hostname {self.hostname}"]

    # Adds the interfaces
    def add_interface(self, *new_interfaces: PhysicalInterface | Loopback) -> None:
        # Check if all the interfaces are either a physical interface or a loopback
        if not all(isinstance(interface, (PhysicalInterface, Loopback)) for interface in new_interfaces):
            raise TypeError("All interfaces should be either a physical interface (e.g. GigabitEthernet) or a loopback")

        # Loop through each new interfaces
        for interface in new_interfaces:
            # First, you check for matching port number and Network IP, to avoid overlapping
            if interface.ip_address and interface.subnet_mask:
                networks = [inf.network_address() for inf in self.all_interfaces() if inf.ip_address]
                if interface.network_address() in networks:
                    raise NetworkError(f"ERROR: Overlapping networks in '{str(interface)}'")

            # For Connectors and Cables
            if isinstance(interface, PhysicalInterface):
                ports = [inf.port for inf in self.__phys_interfaces]

                if interface.port in ports:
                    raise NetworkError(f"ERROR: Overlapping ports in '{interface.port}'")

                self.__phys_interfaces.append(interface)

            # For Loopbacks
            elif isinstance(interface, Loopback):
                ports = [inf.port for inf in self.__loopbacks]
                interface.port = smallest_missing_non_negative_integer(ports)
                self.__loopbacks.append(interface)

    def remove_interface(self, interface_or_port: str | PhysicalInterface | Loopback) -> PhysicalInterface | Loopback:
        if isinstance(interface_or_port, str):  # If it is a port number
            interface = self.interface(interface_or_port)
        else:
            interface = interface_or_port

        if isinstance(interface, PhysicalInterface):
            self.__phys_interfaces.remove(interface)

        elif isinstance(interface, Loopback):
            self.__loopbacks.remove(interface)

        return interface

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

        """
        NOTE: For this configuration, only the hostname configuration is added. There are more lines of code in routers
        and switches.
        """
        # Iterate through each interface
        for interface in self.all_interfaces():
            script.extend(interface.generate_command_block())

        script.append("end")
        NetworkDevice.print_script(script, Fore.GREEN)
