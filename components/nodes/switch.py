from __future__ import annotations

from components.nodes.node import Node, InterfaceList
from components.interfaces.vlan import VLAN
from components.nodes.notfound_error import NotFoundError
from typing import List
from enum import Enum
from colorama import Fore, Style

from components.interfaces.connector import Connector


class Mode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2


class SwitchInterface(Connector):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, bandwidth: int = None, mtu: int = 1500,
                 duplex: str = "auto") -> None:

        super().__init__(int_type, port, cidr, bandwidth, mtu, duplex)
        self.vlan_ids = set()
        self.__switchport_mode = Mode.NULL
        self.dtp_enabled = True

    # VLAN Functions
    def __access_command(self) -> List[str]:
        ios_commands = []

        if len(self.vlan_ids) == 1:

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                f"switchport access vlan {list(self.vlan_ids)[0]}",
                "exit"
            ]

            if self.__switchport_mode != Mode.ACCESS:
                self.__switchport_mode = Mode.ACCESS
                ios_commands.insert(1, "switchport mode access")

            if self.dtp_enabled:
                ios_commands.insert(len(ios_commands) - 1, "switchport nonegotiate")
                self.dtp_enabled = False

        else:
            print(f"{Fore.YELLOW}REFUSED: This connector should hold only one VLAN{Style.RESET_ALL}")

        return ios_commands

    def __disable_both_command(self) -> List[str]:
        ios_commands = []

        # For this command to work, the VLAN ID list must be empty
        if not self.vlan_ids:
            self.__switchport_mode = Mode.NULL

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "no switchport mode trunk",
                "no switchport mode access",
                "exit"
            ]
        else:
            print(f"{Fore.YELLOW}REFUSED: Non-empty VLAN list{Style.RESET_ALL}")

        return ios_commands

    def __trunk_command(self, *vlan_ids: int) -> List[str]:

        ios_commands = []

        if self.__switchport_mode != Mode.TRUNK:
            self.__switchport_mode = Mode.TRUNK

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "switchport trunk encapsulation dot1q",
                # switchport trunk native vlan <native_vlan_id>
                "switchport mode trunk",
                "exit"
            ]
            if vlan_ids:
                ios_commands.insert(2,
                                    f"switchport trunk allowed vlan {','.join(str(vlan_id) for vlan_id in self.vlan_ids)}")

        elif vlan_ids:
            ios_commands = [
                f"interface {self.int_type}{self.port}",
                # switchport trunk native vlan <native_vlan_id>
                f"switchport trunk allowed vlan add {','.join(str(vlan_id) for vlan_id in vlan_ids)}",
                "exit"
            ]

        if self.dtp_enabled:
            ios_commands.insert(len(ios_commands) - 2, "switchport nonegotiate")
            self.dtp_enabled = False

        return ios_commands

    def __trunk_replace_command(self, *vlan_ids: int) -> List[str]:

        ios_commands = [
            f"interface {self.int_type}{self.port}",
            "exit"
        ]

        if vlan_ids:
            ios_commands.insert(1, f"switchport trunk allowed vlan "
                                   f"{','.join(str(vlan_id) for vlan_id in vlan_ids)}")

        if self.__switchport_mode != Mode.TRUNK:
            self.__switchport_mode = Mode.TRUNK
            ios_commands.insert(1, "switchport trunk encapsulation dot1q")
            ios_commands.insert(3, "switchport mode trunk")

        return ios_commands

    def __trunk_remove_command(self, vlan_id: int) -> List[str]:
        if self.__switchport_mode != Mode.TRUNK:
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
        if not all(isinstance(vlan_id, int) for vlan_id in vlan_ids):
            raise TypeError("All VLAN IDs must be an integer")

        # Add the VLAN IDs to the set
        for vlan_id in vlan_ids:
            self.vlan_ids.add(vlan_id)

        if len(self.vlan_ids) > 1 or isinstance(self.destination_node, Switch):  # Multiple VLANs
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

        self.vlan_ids = set(vlan_ids)

        if len(self.vlan_ids) > 1 or isinstance(self.destination_node, Switch):  # Multiple VLANs
            return self.__trunk_replace_command(*vlan_ids)
        else:
            return self.__access_command()

    def remove_vlan(self, vlan_id: int) -> List[str]:

        if not isinstance(vlan_id, int):
            raise TypeError("VLAN ID must be an integer")

        self.vlan_ids.discard(vlan_id)

        if len(self.vlan_ids) > 1 or isinstance(self.destination_node, Switch):  # Multiple VLANs
            return self.__trunk_remove_command(vlan_id)
        elif len(self.vlan_ids) == 1:
            return self.__access_command()
        else:
            self.__switchport_mode = Mode.NULL
            if isinstance(self.destination_node, Switch):
                return self.__trunk_command()
            else:
                return self.__disable_both_command()

    def default_trunk(self):
        self.__switchport_mode = Mode.NULL
        self.vlan_ids.clear()
        return self.__trunk_command()

    def __and__(self, other):
        if isinstance(other, SwitchInterface):
            return self.int_type == other.int_type \
                and self.bandwidth == other.bandwidth \
                and self.mtu == other.mtu \
                and self.duplex == other.duplex \
                and self.destination_node == other.destination_node \
                and self.__switchport_mode == other.__switchport_mode \
                and self.__switchport_mode in [Mode.ACCESS, Mode.TRUNK] \
                and self.vlan_ids == other.vlan_ids

        return False


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


class Switch(Node):

    def __init__(self, node_id: str | int, hostname: str = "Switch", x: int = 0, y: int = 0,
                 interfaces: InterfaceList = None):

        if interfaces:
            if not all(isinstance(interface, SwitchInterface) for interface in interfaces):
                raise TypeError("Switches only accept connectors of type SwitchInterface()")

        super().__init__(node_id, hostname, x, y, interfaces)
        self.vlans = []
        self.__spanning_tree = True

    # VLAN Getter by ID
    def vlan(self, vlan_id: int) -> VLAN | None:

        for vlan in self.vlans:
            if vlan.vlan_id == vlan_id:
                return vlan

        return None

    def get_vlan_dict(self) -> dict:
        dictionary = dict()

        for vlan in self.vlans:
            if vlan.vlan_id not in dictionary.keys():
                dictionary[vlan.vlan_id] = []

            for interface in self.interfaces:
                if vlan.vlan_id in interface.vlan_ids:
                    dictionary[vlan.vlan_id].append(interface.port)

        return dictionary

    # VLAN operations ==============================================================================================
    def add_vlan(self, vlan_id: int, name: str = None, cidr=None):
        if self.vlan(vlan_id):
            raise ValueError(f"VLAN with ID {vlan_id} already exists")

        self.vlans.append(VLAN(vlan_id, name, cidr))
        self._add_cmds(*self.vlans[len(self.vlans) - 1].config())

    # Assign VLANs
    def assign_vlan(self, *vlan_ids: int, ports: str | list | tuple = None, replace: bool = False):
        # Validation
        for vlan_id in vlan_ids:
            if not self.vlan(vlan_id):
                raise NotFoundError(f"VLAN {vlan_id} not found")

        if not ports:
            raise ValueError("Missing parameter 'ports': Which of the ports should I assign the VLANs to?")

        # If only one port is assigned
        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            if replace:
                pass
                self._add_cmds(*interface.replace_vlan(*vlan_ids))
            else:
                self._add_cmds(*interface.assign_vlan(*vlan_ids))

    def detach_vlan(self, vlan_id: int, ports: str | list | tuple = None):
        if not self.vlan(vlan_id):
            raise NotFoundError(f"VLAN {vlan_id} not found")

        if not ports:
            raise ValueError("Missing parameter 'ports': Which of the ports should I assign the VLANs to?")

        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            self._add_cmds(*interface.remove_vlan(vlan_id))

    def default_trunk(self, *ports: str):
        for interface in self.get_ints(*ports):
            self._add_cmds(*interface.default_trunk())

    # Spanning-tree (Only the basics) =========================================================
    def enable_stp(self):

        if self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already enabled{Style.RESET_ALL}")
        else:
            self.__spanning_tree = True

            self._add_cmds("spanning-tree vlan 1")
            for vlan in self.vlans:
                self._add_cmds(f"spanning-tree vlan {vlan.vlan_id}")

    def disable_stp(self):

        if not self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already disabled{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}WARNING: Disabling spanning tree can lead to network loops, broadcast storms, "
                  f"and other issues if not managed carefully.{Style.RESET_ALL}")

            self.__spanning_tree = False

            self._add_cmds("no spanning-tree vlan 1")
            for vlan in self.vlans:
                self._add_cmds(f"no spanning-tree vlan {vlan.vlan_id}")

    # Etherchannel =================================================================================