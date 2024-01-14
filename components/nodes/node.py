from __future__ import annotations

from typing import List, Tuple
from components.interfaces.interface_list import InterfaceList, Connector
from components.interfaces.interface import Interface
from components.interfaces.loopback import Loopback
from components.nodes.notfound_error import NotFoundError
from colorama import Style, Fore
import pyperclip



class Node:

    def __init__(self, node_id: str | int, hostname: str = "Node", x: int = 0, y: int = 0,
                 interfaces: List[Interface] | Tuple[Interface] = None) -> None:
        
        self.node_id = node_id
        self.hostname = hostname
        self.x = x
        self.y = y
        self.cfg_commands = ["configure terminal", f"hostname {hostname}", "end\n"]

        if interfaces is None:
            interfaces = []

        self.interfaces = InterfaceList()
        self.add_int(*interfaces)

    def _add_cmds(self, *commands: str):
        end_ = self.cfg_commands.pop()
        self.cfg_commands.extend(list(commands))
        self.cfg_commands.append(end_)

    def get_int(self, port: str):
        return self.interfaces[port]

    def get_ints(self, *ports: str):
        result = [self.interfaces[port] for port in ports]
        if any(interface is None for interface in result):
            raise NotFoundError(f"One of the interfaces is not included in "
                                f"the list of ports: {str(self.interfaces)}")

        return result

    def set_hostname(self, hostname: str):
        self.hostname = hostname
        self.__add_cmds(f"hostname {hostname}")

    def set_position(self, x: int = None, y: int = None):
        if x:
            self.x = x
        if y:
            self.y = y

    def get_loopback(self, loopback_id: int):
        return self.interfaces[f"L{loopback_id}"]

    def add_int(self, *interfaces: Connector | Loopback) -> None:
        self.interfaces.push(*interfaces)

        for interface in interfaces:
            if isinstance(interface, Connector):
                self._add_cmds(
                    *interface.config(bandwidth=interface.bandwidth, mtu=interface.mtu, duplex=interface.duplex)
                )
            else:
                self._add_cmds(
                    *interface.config()
                )

    def move_int(self, interface: str | Interface) -> Interface:
        return self.interfaces.pop(interface)
    
    def connect(self, port: str, destination_node: Node):
        if not isinstance(destination_node, Node):
            raise TypeError(f"That's not a router, switch or any endpoint device: {str(destination_node)}")
        
        if not isinstance(self.interfaces[port], Connector):
            raise TypeError(f"The interface at port '{port}' is not a connector")
        
        self._add_cmds(
            self.interfaces[port].connect_to(destination_node)
        )

    def send_command(self):
        for command in self.cfg_commands:
            print(f"{Fore.GREEN}{command}{Style.RESET_ALL}")

        # pyperclip.copy("\n".join(self.cfg_commands)) # This will be replaced with netmiko soon

        # self.cfg_commands = ["configure terminal", "end"]

