from __future__ import annotations

from typing import List, Iterable
from components.interfaces.interface_list import InterfaceList, Connector
from components.interfaces.interface import Interface
from components.interfaces.loopback import Loopback
from components.nodes.notfound_error import NotFoundError
from colorama import Style, Fore
import re
# import pyperclip


class NetworkDevice:

    hostname_pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    hostname_regex = re.compile(hostname_pattern)

    @staticmethod
    def print_script(commands: Iterable[str], color = Fore.WHITE):
        for command in commands:
            print(f"{color}{command}{Style.RESET_ALL}")

    # Constructor
    def __init__(self, node_id: str | int = None, hostname: str = "NetworkDevice", x: int = 0, y: int = 0,
                 interfaces: Iterable[Connector] = None) -> None:
        
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
        return f"Device {self.hostname}"

    def __eq__(self, other):
        if isinstance(other, NetworkDevice):
            return self.__device_id == other.__device_id \
                and self.hostname == other.hostname

    def __hash__(self):
        return hash((self.__device_id, self.hostname))

    # Sends Cisco command to script
    def __getitem__(self, port: str) -> Connector:
        return self.interfaces[port]

    # Getters
    def get_id(self):
        return self.__device_id

    def get_int(self, port: str) -> Connector:  # Get interface
        return self.interfaces[port]

    def get_ints(self, *ports: str) -> List[Connector]:
        result = [self.interfaces[port] for port in ports]
        if any(interface is None for interface in result):
            raise NotFoundError(f"ERROR: One of the interfaces is not included in "
                                f"the list of ports: {str(self.interfaces)}")

        return result

    # def get_loopback(self, loopback_id: int) -> Loopback:
    #     return self.interfaces[f"L{loopback_id}"]

    def get_remote_device(self, port):
        device = self.get_int(port).remote_device
        if device is None:
            print(f"{Fore.YELLOW}WARNING: Dangling connector '{self.get_int(port)}', so no remote device{Style.RESET_ALL}")

        return device

    def get_remote_port(self, port):
        remote_port = self.get_int(port).remote_port
        if remote_port is None:
            print(
                f"{Fore.YELLOW}WARNING: Dangling connector '{self.get_int(port)}', so no remote device{Style.RESET_ALL}")

        return remote_port

    # Setters
    def update_id(self, new_id: int | str) -> None:
        self.__device_id = new_id

    def _set_hostname(self, hostname: str):

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

    def connect(self, port: str, remote_device: NetworkDevice, remote_port: int | str):
        if not isinstance(remote_device, NetworkDevice):
            raise TypeError(f"ERROR: This is not a networking device: {str(remote_device)}")

        if remote_device == self:
            raise ConnectionError(f"ERROR: Cannot connect interface to itself")

        if not isinstance(self.interfaces[port], Connector):
            if self[port] is None:
                raise TypeError(f"ERROR: The interface at port '{port}' does not exist")
            else:
                raise TypeError(f"ERROR: The interface at port '{port}' is not a connector")

        if self[port].remote_device is not None:
            raise ConnectionError(f"ERROR at '{str(self)}': {str(self[port])}"
                                  f" already connected")

        self[port].connect_to(remote_device, remote_port)
        if remote_device[remote_port].bandwidth < self[port].bandwidth:
            self[port].config(bandwidth=remote_device[remote_port].bandwidth)

    def disconnect(self, port: str):
        self.interfaces[port].disconnect()

    def send_script(self) -> List[str]:
        script = ["configure terminal"]

        if self._changes_made["hostname"]:
            script.append(f"hostname {self.hostname}")
            self._changes_made["hostname"] = False
        
        for interface in self.interfaces:
            script.extend(interface.get_command_block())

        script.append("end")

        return script

        # self.script = ["configure terminal", "end"]
