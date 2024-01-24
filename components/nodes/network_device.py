from __future__ import annotations

from typing import List, Iterable
from components.interfaces.interface_list import InterfaceList, Connector
from components.interfaces.interface import Interface
from components.interfaces.loopback import Loopback
from components.nodes.notfound_error import NotFoundError
from colorama import Style, Fore
import re
import pyperclip


class NetworkDevice:

    hostname_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    hostname_regex = re.compile(hostname_pattern)

    @staticmethod
    def print_script(commands: Iterable[str], color = Fore.WHITE):
        for command in commands:
            print(f"{color}{command}{Style.RESET_ALL}")

    # Constructor
    def __init__(self, node_id: str | int, hostname: str = "Node", x: int = 0, y: int = 0,
                 interfaces: Iterable[Interface] = None) -> None:
        
        if not NetworkDevice.hostname_regex.match(hostname):
            raise ValueError(f"ERROR: '{hostname}' is not a valid hostname")

        self.__device_id = node_id
        self.hostname = hostname
        self.x = x
        self.y = y

        self._changes_made = {"hostname": True}

        if interfaces is None:
            interfaces = []

        self.interfaces = InterfaceList()
        self.add_int(*interfaces)

    # Couple of operators
    def __str__(self):
        interfaces_qty = len(self.interfaces)
        return f"<Device {self.hostname} with {interfaces_qty} interface(s)>"

    def __eq__(self, other):
        if isinstance(other, NetworkDevice):
            return self.__device_id == other.__device_id \
                and self.hostname == other.hostname \
                and (self.x, self.y) == (other.x, other.y)

    # Sends Cisco command to script
    def _to_script(self, *commands: str):
        end_ = self.script.pop()
        self.script.extend(list(commands))
        self.script.append(end_)
    
    def __getitem__(self, port: str) -> Connector | Loopback:
        return self.interfaces[port]

    # Getters
    def get_int(self, port: str) -> Connector | Loopback:  # Get interface
        return self.interfaces[port]

    def get_ints(self, *ports: str) -> List[Connector | Loopback]:
        result = [self.interfaces[port] for port in ports]
        if any(interface is None for interface in result):
            raise NotFoundError(f"ERROR: One of the interfaces is not included in "
                                f"the list of ports: {str(self.interfaces)}")

        return result

    def get_loopback(self, loopback_id: int) -> Loopback:
        return self.interfaces[f"L{loopback_id}"]

    def get_destination_device(self, port):
        device = self.get_int(port).destination_device
        if device is None:
            print(f"{Fore.YELLOW}WARNING: Dangling connector '{self.get_int(port)}', so no destination device{Style.RESET_ALL}")

        return device

    def get_destination_port(self, port):
        destination_port = self.get_int(port).destination_port
        if destination_port is None:
            print(
                f"{Fore.YELLOW}WARNING: Dangling connector '{self.get_int(port)}', so no destination device{Style.RESET_ALL}")

        return destination_port

    # Setters
    def set_hostname(self, hostname: str):

        if not NetworkDevice.hostname_regex.match(hostname):
            raise ValueError(f"ERROR: '{hostname}' is not a valid hostname")
        
        self.hostname = hostname

    def set_position(self, x: int = None, y: int = None):
        if x:
            self.x = x
        if y:
            self.y = y

    def shutdown(self, port: str) -> None:
        self.get_int(port).shutdown()

    def release(self, port: str) -> None:
        self.get_int(port).release()

    def add_int(self, *interfaces: Connector | Loopback) -> None:
        self.interfaces.push(*interfaces)

    def remove_int(self, interface: str | Connector | Loopback) -> Connector | Loopback:
        return self.interfaces.pop(interface)

    def connect(self, port: str, destination_device: NetworkDevice, destination_port: int | str = None):
        if not isinstance(destination_device, NetworkDevice):
            raise TypeError(f"ERROR: This is not a networking device: {str(destination_device)}")

        if destination_device == self:
            raise ConnectionError(f"ERROR: Cannot connect interface to itself")

        if not isinstance(self.interfaces[port], Connector):
            if self.interfaces[port] is None:
                raise TypeError(f"ERROR: The interface at port '{port}' does not exist")
            else:
                raise TypeError(f"ERROR: The interface at port '{port}' is not a connector")

        self.interfaces[port].connect_to(destination_device, destination_port)

    def disconnect(self, port: str):
        self.interfaces[port].disconnect()

    def submit_script(self) -> List[str]:
        script = ["configure terminal"]

        if self._changes_made["hostname"]:
            script.append(f"hostname {self.hostname}")
            self._changes_made["hostname"] = False
        
        for interface in self.interfaces:
            script.extend(interface.get_command_block())

        script.append("end")

        return script

        # self.script = ["configure terminal", "end"]
