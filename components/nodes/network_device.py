from __future__ import annotations

from typing import List, Tuple, Any
from components.interfaces.interface_list import InterfaceList, Connector
from components.interfaces.interface import Interface
from components.interfaces.loopback import Loopback
from components.nodes.notfound_error import NotFoundError
from colorama import Style, Fore
import pyperclip


class NetworkDevice:

    def __init__(self, node_id: str | int, hostname: str = "Node", x: int = 0, y: int = 0,
                 interfaces: List[Interface] | Tuple[Interface] = None) -> None:

        self.device_id = node_id
        self.hostname = hostname
        self.x = x
        self.y = y
        self.script = ["configure terminal", f"hostname {hostname}", "end\n"]

        if interfaces is None:
            interfaces = []

        self.interfaces = InterfaceList()
        self.add_int(*interfaces)

    def __str__(self):
        interfaces_qty = len(self.interfaces)
        return f"<Device {self.hostname} with {interfaces_qty} interface(s)>"

    def __eq__(self, other):
        if isinstance(other, NetworkDevice):
            return self.device_id == other.device_id \
                and self.hostname == other.hostname \
                and (self.x, self.y) == (other.x, other.y)

    def _to_script(self, *commands: str):
        end_ = self.script.pop()
        self.script.extend(list(commands))
        self.script.append(end_)

    def get_int(self, port: str) -> Interface:  # Get interface
        return self.interfaces[port]

    def get_ints(self, *ports: str) -> List[Interface]:
        result = [self.interfaces[port] for port in ports]
        if any(interface is None for interface in result):
            raise NotFoundError(f"ERROR: One of the interfaces is not included in "
                                f"the list of ports: {str(self.interfaces)}")

        return result

    def get_loopback(self, loopback_id: int):
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

    def set_hostname(self, hostname: str):
        self.hostname = hostname
        self._to_script(f"hostname {hostname}")

    def set_position(self, x: int = None, y: int = None):
        if x:
            self.x = x
        if y:
            self.y = y

    def add_int(self, *interfaces: Connector | Loopback) -> None:
        self.interfaces.push(*interfaces)

        for interface in interfaces:
            if isinstance(interface, Connector):
                self._to_script(
                    *interface.config(bandwidth=interface.bandwidth, mtu=interface.mtu, duplex=interface.duplex)
                )
            else:
                self._to_script(
                    *interface.config()
                )

    def move_int(self, interface: str | Interface) -> Interface:
        return self.interfaces.pop(interface)

    def shutdown(self, port):
        ios_commands = self.interfaces[port].set_shutdown(True)

        if ios_commands:
            if f"interface {self.get_int(port).int_type}{port}" in self.script:

                index = self.script.index(f"interface {self.get_int(port).int_type}{port}") + 1
                while self.script[index] != "exit":
                    if self.script[index] == "no shutdown":
                        self.script[index] = "shutdown"
                        break

                    index += 1

            else:
                self._to_script(*ios_commands)

    def release(self, port):
        ios_commands = self.interfaces[port].set_shutdown(False)

        if ios_commands:
            if f"interface {self.get_int(port).int_type}{port}" in self.script:

                index = self.script.index(f"interface {self.get_int(port).int_type}{port}") + 1
                while self.script[index] != "exit":
                    if self.script[index] == "shutdown":
                        self.script[index] = "no shutdown"
                        break

                    index += 1

            else:
                self._to_script(*ios_commands)

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

        # Incorporate the 'no shutdown' command into the script
        self.interfaces[port].connect_to(destination_device, destination_port)
        self.release(port)

    def disconnect(self, port: str):
        self.shutdown(port)
        self.interfaces[port].disconnect()

    def send_script(self):
        for command in self.script:
            print(f"{Fore.GREEN}{command}{Style.RESET_ALL}")

        pyperclip.copy("\n".join(self.script))  # This will be replaced with netmiko soon

        # self.script = ["configure terminal", "end"]
