from __future__ import annotations

from typing import List, Iterable, Type
from iptx_utils import NetworkError
from components.interfaces.physical_interfaces.physical_interface import PhysicalInterface
from components.interfaces.interface import Interface
from components.interfaces.loopback import Loopback
from iptx_utils import NotFoundError, next_number
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
        for command in commands:
            print(f"{color}{command}{Style.RESET_ALL}")

    # Constructor
    def __init__(self, device_id: str | int = None, hostname: str = "NetworkDevice",
                 interfaces: Iterable[PhysicalInterface] = None) -> None:

        # Hostname validation
        if not NetworkDevice.hostname_regex.match(hostname):
            raise ValueError(f"ERROR: '{hostname}' is not a valid hostname")

        # If the interface is not given
        if interfaces is None:
            interfaces = []

        # Attributes
        self.__device_id = device_id
        self.hostname = hostname
        self.__phys_interfaces = []
        self.__loopbacks = []
        self.add_interface(*interfaces)

        # Cisco commands
        self.__hostname_cmd = f"hostname {self.hostname}"

    # Stringify
    def __str__(self):
        return f"Device {self.hostname}"

    # The equal and hashable operator are for identification
    def __eq__(self, other):
        if isinstance(other, NetworkDevice):
            return self.__device_id == other.__device_id \
                and self.hostname == other.hostname

    def __hash__(self):
        return hash((self.__device_id, self.hostname))

    # Getters ---------------------------------------------------------------
    def id(self):
        return self.__device_id

    def interface(self, port: str) -> PhysicalInterface | None:
        for interface in self.__phys_interfaces:
            if port == interface.port:
                return interface

        # Raise an error if it doesn't exist
        raise NotFoundError(f"ERROR in {self.hostname}: Interface with port {port} is not included in "
                            f"this network device")

    def interface_range(self, *ports: str) -> List[PhysicalInterface]:
        return [self.interface(port) for port in ports]

    def loopback(self, loopback_id: int) -> Loopback:
        for interface in self.__loopbacks:
            if loopback_id == interface.port:
                return interface

        # Raise an error if it doesn't exist
        raise NotFoundError(f"ERROR in {self.hostname}: Loopbacks with ID {loopback_id} is not included in "
                            f"this network device")

    def all_phys_interfaces(self):
        return self.__phys_interfaces

    def all_loopbacks(self):
        return self.__loopbacks

    def all_interfaces(self):
        return self.__phys_interfaces + self.__loopbacks

    def remote_device(self, port):
        device = self.interface(port).remote_device
        if device is None:
            print(
                f"{Fore.YELLOW}WARNING: Unconnected '{self.interface(port)}', so no remote device{Style.RESET_ALL}")

        return device

    def remote_port(self, port):
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
    def set_hostname(self, hostname: str):

        if not NetworkDevice.hostname_regex.match(hostname):
            raise ValueError(f"ERROR: '{hostname}' is not a valid hostname")

        self.hostname = hostname
        self.__hostname_cmd = f"hostname {self.hostname}"

    # Adds the interfaces
    def add_interface(self, *new_interfaces: PhysicalInterface | Loopback) -> None:
        # Check if all the interfaces are either a physical interface or a loopback
        if not all(isinstance(interface, (PhysicalInterface, Loopback)) for interface in new_interfaces):
            raise TypeError("All interfaces should be either a connector (e.g. GigabitEthernet) or a loopback")

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
                interface.port = next_number(ports)
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

    # Establish connection
    def connect(self, port: str, remote_device: Type[NetworkDevice], remote_port: int | str) -> None:
        # Data type validation
        if not isinstance(remote_device, NetworkDevice):
            raise TypeError(f"ERROR in device {self.hostname}: This is "
                            f"not a networking device: {str(remote_device)}")

        # Disallows connection to itself
        if remote_device == self:
            raise ConnectionError(f"ERROR in device {self.hostname}: "
                                  f"Cannot connect interface to itself")

        # If the port is not a physical interface
        if not isinstance(self.interface(port), PhysicalInterface):
            raise TypeError(f"ERROR in device '{str(self)}': The interface at port '{port}' "
                            f"is not a physical interface")

        # If the port is already connected
        if self.interface(port).remote_device is not None:
            raise ConnectionError(f"ERROR in device '{str(self)}': {str(self.interface(port))}"
                                  f" already connected")

        self.interface(port).connect_to(remote_device, remote_port)

        # Cap the bandwidth to an interface of the lowest bandwidth
        if remote_device.interface(remote_port).bandwidth < self.interface(port).bandwidth:
            self.interface(port).config(bandwidth=remote_device[remote_port].bandwidth)

        # Sets the MTU to 1500 by default if there's a mismatch
        if remote_device.interface(remote_port).mtu != self.interface(port).mtu:
            self.interface(port).config(mtu=remote_device[remote_port].mtu)

    def disconnect(self, port: str):
        self.interface(port).disconnect()

    def send_script(self) -> List[str]:
        script = ["configure terminal"]

        if self.__hostname_cmd:
            script.append(f"hostname {self.hostname}")
            self.__hostname_cmd = ""

        for interface in self.all_interfaces():
            script.extend(interface.generate_command_block())

        script.append("end")
        return script

