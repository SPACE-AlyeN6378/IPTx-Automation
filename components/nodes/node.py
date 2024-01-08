from __future__ import annotations

from enum import Enum
from typing import Type
from components.interfaces.interface_list import InterfaceList, Connector
from components.interfaces.interface import Interface
from components.nodes.notfound_error import NotFoundError



class Node:

    def __init__(self, node_id: str | int, hostname: str = "Node", x: int = 0, y: int = 0,
                 interfaces: InterfaceList = None) -> None:
        if interfaces is None:
            interfaces = InterfaceList()

        self.node_id = node_id
        self.hostname = hostname
        self.x = x
        self.y = y
        self.interfaces = interfaces
        self.cfg_commands = []

    def get_int(self, port: str):
        return self.interfaces[port]

    def get_ints(self, *ports: str):
        result = [self.interfaces[port] for port in ports]
        if any(interface is None for interface in result):
            raise NotFoundError(f"One of the interfaces is not included in "
                                f"the list of ports: {str(self.interfaces)}")

        return result

    def get_loopback(self, loopback_id: int):
        return self.interfaces[f"L{loopback_id}"]

    def add_int(self, interface: Interface) -> None:
        self.interfaces.push(interface)

    def move_int(self, interface: str | Interface) -> Interface:
        return self.interfaces.pop(interface)
    


    def generate_ip_config(self):
        ios_commands = []
        for interface in self.interfaces:
            ios_commands.extend(interface.config() + ["!"])

        return ios_commands
    
    def connect(self, port: str, destination_node):
        if not isinstance(destination_node, Node):
            return TypeError(f"That's not a router, switch or any endpoint device: {str(destination_node)}")
        
        if not isinstance(self.interfaces[port], Connector):
            return TypeError(f"The interface at port '{port}' is not a connector")
        
        self.interfaces[port].connect_to(destination_node)

class Endpoint(Node):
    pass
