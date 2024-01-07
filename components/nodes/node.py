from typing import Type
from components.interfaces.interface_list import InterfaceList, Connector
from components.interfaces.interface import Interface


class Node:

    def __init__(self, node_id: str | int, hostname: str = "Node", x: int = 0, y: int = 0,
                 interfaces: InterfaceList=None) -> None:
        if interfaces is None:
            interfaces = InterfaceList()

        self.node_id = node_id
        self.hostname = hostname
        self.x = x
        self.y = y
        self.interfaces = interfaces
        self.cfg_commands = []

    def add_interface(self, interface: Interface) -> None:
        self.interfaces.push(interface)

    def move_interface(self, interface: str | Interface) -> Interface:
        return self.interfaces.pop(interface)
    
    def get_interface(self, port: str):
        return self.interfaces[port]

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
