from __future__ import annotations

from components.nodes.node import Node, InterfaceList
from components.interfaces.vlan import VLAN
from components.nodes.notfound_error import NotFoundError
from typing import List, Tuple 
from enum import Enum

from components.interfaces.connector import Connector, Duplex


class Mode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2

class Task(Enum):
    ADD = 3
    REPLACE = 4
    DELETE = 5


class SwitchInterface(Connector):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, bandwidth: int = None, mtu: int = 1500,
                 duplex: str = Duplex.AUTO, vlan_ids=None) -> None:
        if vlan_ids is None:
            vlan_ids = set()
        if not isinstance(vlan_ids, set):
            raise TypeError("Use sets for storing VLAN IDs to maintain uniqueness")

        super().__init__(int_type, port, cidr, bandwidth, mtu, duplex)
        self.vlan_ids = vlan_ids
        self.__switch_mode = Mode.NULL

    # VLAN Functions
    def __access_command(self) -> List[str]:
        ios_commands = []

        if len(self.vlan_ids) == 1:
            if self.__switch_mode != Mode.ACCESS:
                self.__switch_mode = Mode.ACCESS

                ios_commands = [
                    f"interface {self.int_type}{self.port}",
                    "switchport mode access",
                    f"switchport access vlan {list(self.vlans)[0]}",
                    "switchport nonegotiate",
                    "exit"
                ]

            else:
                ios_commands = [
                    f"interface {self.int_type}{self.port}",
                    f"switchport access vlan {list(self.vlans)[0]}",
                    "exit"
                ]
        else:
            print("\n* REFUSED: This connector should hold only one VLAN")

        return ios_commands

    def __disable_both_command(self) -> List[str]:
        ios_commands = []

        if not self.vlans:
            self.__switch_mode = Mode.NULL

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "no switchport mode trunk",
                "no switchport mode access",
                "exit"
            ]
        else:
            print("* REFUSED: Non-empty VLAN list")

        return ios_commands

    def __trunk_command(self, *vlan_ids: int) -> List[str]:

        ios_commands = []

        if self.__switch_mode != Mode.TRUNK:
            self.__switch_mode = Mode.TRUNK

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "switchport trunk encapsulation dot1q",
                # switchport trunk native vlan <native_vlan_id>
                f"switchport trunk allowed vlan {','.join(str(vlan_id) for vlan_id in self.vlans)}",
                "switchport mode trunk",
                "switchport nonegotiate",
                "exit"
            ]
            if vlan_ids:
                ios_commands.insert(2, f"switchport trunk allowed vlan {','.join(str(vlan_id) for vlan_id in self.vlans)}")


        elif vlan_ids:
            ios_commands = [
                f"interface {self.int_type}{self.port}",
                # switchport trunk native vlan <native_vlan_id>
                f"switchport trunk allowed vlan add {','.join(str(vlan_id) for vlan_id in vlan_ids)}",
                "exit"
            ]

        return ios_commands

    def __trunk_replace_command(self, *vlan_ids: int) -> List[str]:

        if not vlan_ids:
            raise ValueError("Parameters for VLAN IDs are missing")

        ios_commands = [
            f"interface {self.int_type}{self.port}",
            f"switchport trunk allowed vlan {','.join(str(vlan_id) for vlan_id in vlan_ids)}",
            "exit"
        ]

        if self.__switch_mode != Mode.TRUNK:
            self.__switch_mode = Mode.TRUNK
            ios_commands.insert(1, "switchport trunk encapsulation dot1q")
            ios_commands.insert(3, "switchport mode trunk")

        return ios_commands

    def __trunk_remove_command(self, vlan_id: int) -> List[str]:
        if self.__switch_mode != Mode.TRUNK:
            raise ConnectionError("This connector is not in switchport trunk mode")

        ios_commands = [
            f"interface {self.int_type}{self.port}",
            f"switchport trunk allowed vlan remove {vlan_id}",
            "exit"
        ]

        return ios_commands

    # These VLAN assignment functions will be used outside the class structure ===================================
    def assign_vlan(self, *vlan_ids: int) -> List[str]:
        # No empty parameters
        if not vlan_ids:
            raise ValueError("Missing parameters for VLAN IDs")
        # All VLAN IDs must be an integer
        if any(not isinstance(vlan_id, int) for vlan_id in vlan_ids):
            raise TypeError("All VLAN IDs must be an integer")

        for vlan_id in vlan_ids:
            self.vlans.add(vlan_id)

        if len(self.vlans) > 1 or isinstance(self.destination_node, Switch):  # Multiple VLANs
            return self.__trunk_command(*vlan_ids)
        else:
            return self.__access_command()

    def replace_vlan(self, *vlan_ids: int) -> List[str]:
        # No empty parameters
        if not vlan_ids:
            raise ValueError("Missing parameters for VLAN IDs")
        # All VLAN IDs must be an integer
        if any(not isinstance(vlan_id, int) for vlan_id in vlan_ids):
            raise TypeError("All VLAN IDs must be an integer")

        self.vlans = set(vlan_ids)

        if len(self.vlans) > 1 or isinstance(self.destination_node, Switch)::  # Multiple VLANs
            return self.__trunk_replace_command(*vlan_ids)
        else:
            return self.__access_command()

    def remove_vlan(self, vlan_id: int, trunking: bool = False) -> List[str]:

        if not isinstance(vlan_id, int):
            raise TypeError("VLAN ID must be an integer")

        self.vlans.discard(vlan_id)

        if len(self.vlans) > 1 or trunking:  # Multiple VLANs
            return self.__trunk_remove_command(vlan_id)
        elif len(self.vlans) == 1:
            return self.__access_command()
        else:
            if not trunking:
                return self.__disable_both_command()





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
    

    
