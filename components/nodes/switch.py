from components.nodes.node import Node, InterfaceList
from components.interfaces.vlan import VLAN
from components.nodes.notfound_error import NotFoundError
from typing import List, Tuple 
from enum import Enum

class Task(Enum):
    ADD = 0
    REPLACE = 1
    DELETE = 2


class Switch(Node):

    def __init__(self, node_id: str | int, hostname: str = "Switch", x: int = 0, y: int = 0, interfaces: InterfaceList=None):
        
        super().__init__(node_id, hostname, x, y, interfaces)
        self.vlans = []

    # VLAN Getter by ID
    def vlan(self, vlan_id: int) -> VLAN:
        
        for vlan in self.vlans:
            if vlan.vlan_id == vlan_id:
                return vlan

        return None
    
    def get_vlan_dict(self) -> dict:
        result = dict()
        for interface in self.interfaces:
            for vlan_id in interface.vlans:
                result[vlan_id] = interface.port

        return result
    
    def add_vlan(self, vlan_id: int, name: str="untitled", cidr=None):
        if self.vlan(vlan_id):
            raise ValueError(f"VLAN with ID {vlan_id} already exists")
        
        self.vlans.append(VLAN(vlan_id, name, cidr))
        self.cfg_commands.extend(self.vlans[len(self.vlans) - 1].config())
    
    # VLANs to Interface
    def add_vlans_to_int(self, port: str, vlan_ids: List[int] | Tuple[int]):
        # Check if the given port number and the VLANs exist
        if not self.interfaces[port]:
            raise NotFoundError(f"Interface with port '{port}' cannot be found on this switch")
        
        if any(self.vlan(vlan_id) == None for vlan_id in vlan_ids):
            raise NotFoundError(f"One or more of the VLANs from the parameter are missing")
        
        trunking_only = isinstance(self.interfaces[port].destination_node, Switch)

        config = self.interfaces[port].assign_vlan(*vlan_ids, trunking=trunking_only)
        self.cfg_commands.extend(config)
        self.cfg_commands.append("!")


    def replace_vlans_in_int(self, port: str, vlan_ids: List[int] | Tuple[int]):
        # Check if the given port number and the VLANs exist
        if not self.interfaces[port]:
            raise NotFoundError(f"Interface with port '{port}' cannot be found on this switch")
        
        if any(self.vlan(vlan_id) == None for vlan_id in vlan_ids):
            raise NotFoundError(f"One or more of the VLANs from the parameter are missing")
        
        trunking_only = isinstance(self.interfaces[port].destination_node, Switch)

        config = self.interfaces[port].replace_vlan(*vlan_ids, trunking=trunking_only)
        self.cfg_commands.extend(config)
        self.cfg_commands.append("!")
    

    def remove_int_from_vlan(self, port: str, vlan_id: int):
        # Check if the given port number and the VLANs exist
        if not self.interfaces[port]:
            raise NotFoundError(f"Interface with port '{port}' cannot be found on this switch")
        
        if not self.vlan(vlan_id):
            raise NotFoundError(f"VLAN {vlan_id} not found")
        
        trunking_only = isinstance(self.interfaces[port].destination_node, Switch)

        config = self.interfaces[port].remove_vlan(vlan_id, trunking=trunking_only)
        self.cfg_commands.extend(config)
        self.cfg_commands.append("!")

    # Interfaces to VLAN
    def add_ints_to_vlan(self, vlan_id: str, ports: List[str] | Tuple[str]):

        if not self.vlan(vlan_id):
            raise NotFoundError(f"VLAN {vlan_id} not found")
        
        for port in ports:
            if not self.interfaces[port]:
                raise NotFoundError(f"Interface with port '{port}' cannot be found on this switch")
            else:
                trunking_only = isinstance(self.interfaces[port].destination_node, Switch)

                config = self.interfaces[port].assign_vlan(vlan_id, trunking=trunking_only)
                self.cfg_commands.extend(config)
                self.cfg_commands.append('!')


    def replace_ints_in_vlan(self, vlan_id: str, ports: List[str] | Tuple[str]):

        if not self.vlan(vlan_id):
            raise NotFoundError(f"VLAN {vlan_id} not found")
        
        for port in ports:
            if not self.interfaces[port]:
                raise NotFoundError(f"Interface with port '{port}' cannot be found on this switch")
            else:
                trunking_only = isinstance(self.interfaces[port].destination_node, Switch)

                config = self.interfaces[port].replace_vlan(vlan_id, trunking=trunking_only)
                self.cfg_commands.extend(config)
                self.cfg_commands.append('!')
    

    
