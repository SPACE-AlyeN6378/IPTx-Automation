from __future__ import annotations

from components.nodes.network_device import NetworkDevice
from components.interfaces.vlan import VLAN
from components.nodes.notfound_error import NotFoundError
from typing import List, Union, Set, Tuple
from enum import Enum
from colorama import Fore, Style

from components.interfaces.connector import Connector


class SwitchMode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2


class Protocol(Enum):
    ECN_PAGP = 3
    ECN_LACP = 4


class SwitchInterface(Connector):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, bandwidth: int = None, mtu: int = 1500,
                 duplex: str = "auto") -> None:

        super().__init__(int_type, port, cidr, bandwidth, mtu, duplex)
        self.vlan_ids = set()
        self.__switchport_mode = SwitchMode.NULL
        self.dtp_enabled = True

        # Etherchannel
        self.port_channel = None
        self.ecn_protocol = None
        self.ecn_unconditional = False

    # VLAN Functions
    def __access_command(self) -> List[str]:
        ios_commands = []

        if len(self.vlan_ids) == 1:

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                f"switchport access vlan {list(self.vlan_ids)[0]}",
                "exit"
            ]

            if self.__switchport_mode != SwitchMode.ACCESS:
                self.__switchport_mode = SwitchMode.ACCESS
                ios_commands.insert(1, "switchport mode access")

            if self.dtp_enabled:
                ios_commands.insert(len(ios_commands) - 1, "switchport nonegotiate")
                self.dtp_enabled = False

        else:
            print(f"{Fore.MAGENTA}DENIED: This connector should hold only one VLAN{Style.RESET_ALL}")

        return ios_commands

    def __disable_both_command(self) -> List[str]:
        ios_commands = []

        # For this command to work, the VLAN ID list must be empty
        if not self.vlan_ids:
            self.__switchport_mode = SwitchMode.NULL

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "no switchport mode trunk",
                "no switchport mode access",
                "exit"
            ]
        else:
            print(f"{Fore.YELLOW}REFUSED: Non-empty VLAN list{Style.RESET_ALL}")

        return ios_commands

    def __trunk_add_command(self, *vlan_ids: int) -> List[str]:

        ios_commands = []

        if self.__switchport_mode != SwitchMode.TRUNK:
            self.__switchport_mode = SwitchMode.TRUNK

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "switchport trunk encapsulation dot1q",
                # switchport trunk native vlan <native_vlan_id>
                "switchport mode trunk",
                "exit"
            ]
            if vlan_ids:
                ios_commands.insert(2, f"switchport trunk allowed vlan"
                                       f" {','.join(str(vlan_id) for vlan_id in self.vlan_ids)}")

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

        if self.__switchport_mode != SwitchMode.TRUNK:
            self.__switchport_mode = SwitchMode.TRUNK
            ios_commands.insert(1, "switchport trunk encapsulation dot1q")
            ios_commands.insert(3, "switchport mode trunk")

        return ios_commands

    def __trunk_remove_command(self, vlan_id: int) -> List[str]:
        if self.__switchport_mode != SwitchMode.TRUNK:
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

        if len(self.vlan_ids) > 1 or isinstance(self.destination_device, Switch):  # Multiple VLANs
            return self.__trunk_add_command(*vlan_ids)
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

        if len(self.vlan_ids) > 1 or isinstance(self.destination_device, Switch):  # Multiple VLANs
            return self.__trunk_replace_command(*vlan_ids)
        else:
            return self.__access_command()

    def remove_vlan(self, vlan_id: int) -> List[str]:

        if not isinstance(vlan_id, int):
            raise TypeError("VLAN ID must be an integer")

        self.vlan_ids.discard(vlan_id)

        if len(self.vlan_ids) > 1 or isinstance(self.destination_device, Switch):  # Multiple VLANs
            return self.__trunk_remove_command(vlan_id)
        elif len(self.vlan_ids) == 1:
            return self.__access_command()
        else:
            self.__switchport_mode = SwitchMode.NULL
            if isinstance(self.destination_device, Switch):
                return self.__trunk_add_command()
            else:
                return self.__disable_both_command()

    # Configure switchport as trunk for all VLANs 1-4094
    def default_trunk(self):
        self.__switchport_mode = SwitchMode.NULL
        self.vlan_ids.clear()
        return self.__trunk_add_command()

    # Check if establishing ether-channels fulfills the required criteria
    def etherchannel_check(self, other):
        # Must be a switch interface
        if not isinstance(other, SwitchInterface):
            raise TypeError(f"ERROR: Only accepts type SwitchInterface()")
        # Interface type
        elif self.int_type != other.int_type:
            raise ValueError(f"ERROR: Mismatching interface type")
        # Bandwidth
        elif self.bandwidth != other.bandwidth:
            raise ValueError(f"ERROR: Mismatching bandwidth")
        # MTU
        elif self.mtu != other.mtu:
            raise ValueError(f"ERROR: Mismatching MTU")
        # Duplex
        elif self.duplex != other.duplex:
            raise ValueError(f"ERROR: Mismatching Duplex")
        # Switchport
        elif self.__switchport_mode != other.__switchport_mode:
            raise ValueError(f"ERROR: Mismatching switchport modes")
        # Valid switchport
        elif self.__switchport_mode not in [SwitchMode.ACCESS, SwitchMode.TRUNK]:
            raise ValueError(f"ERROR: Switchport is neither access nor trunk")
        # Same destination
        elif self.destination_device != other.destination_device:
            raise ConnectionError(f"ERROR: Not connected to the same device")

    def etherchannel(self, port_channel_num: int = None,
                     protocol: Union[Protocol.ECN_LACP, Protocol.ECN_PAGP] = None,
                     unconditional: bool = None):


        # Check for any errors in connection
        if self.destination_device is None:
            raise ConnectionError(f"ERROR: Dangling connector {self.int_type}{self.port}")

        if not isinstance(self.destination_device, Switch):
            raise TypeError("ERROR: Ether-channels only supports switches in this backbone network")

        ios_commands = []

        if self.__switchport_mode == SwitchMode.NULL:
            self.__switchport_mode = SwitchMode.TRUNK
            ios_commands.extend(self.default_trunk())

        else:
            ios_commands = [f"interface {self.int_type}{self.port}"]

        remote_interface = self.destination_device.get_int(self.destination_port)

        # Port channel
        if port_channel_num is None:
            if remote_interface.port_channel is None:
                raise ValueError("ERROR: Port channel number not given. The destination device does not have one.")

            self.port_channel = remote_interface.port_channel
        else:
            if not (1 <= port_channel_num <= 48):
                raise ValueError("ERROR: The port-channel number must be between 1 and 48")

            self.port_channel = port_channel_num
            remote_interface.port_channel = port_channel_num

        # Etherchannel Protocols
        if protocol not in [Protocol.ECN_LACP, Protocol.ECN_PAGP, None]:
            raise ValueError("ERROR: Incorrect protocols. Ether-channels either use PAgP, LACP, or None")

        self.ecn_protocol = protocol

        # Unconditional
        if unconditional is not None:
            self.ecn_unconditional = unconditional

        x = self.ecn_unconditional
        y = remote_interface.ecn_unconditional

        # RULE: If the remote host ECN protocol is conditional, then the source host counterpart
        # should always be set to unconditional, otherwise it's any
        self.ecn_unconditional = (not y) or (x and not y) or (x and y)

        # Generate cisco command
        protocol_keyword = ""
        if self.ecn_protocol == Protocol.ECN_LACP:
            if unconditional:
                protocol_keyword = "active"
            else:
                protocol_keyword = "passive"

        elif self.ecn_protocol == Protocol.ECN_PAGP:
            if unconditional:
                protocol_keyword = "desirable"
            else:
                protocol_keyword = "auto"

        return [f"interface {self.int_type}{self.port}",
                f"channel-group {self.port_channel} mode {protocol_keyword}",
                "exit"]


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


class Switch(NetworkDevice):

    def __init__(self, node_id: str | int, hostname: str = "Switch", x: int = 0, y: int = 0,
                 interfaces: List[SwitchInterface] | Tuple[SwitchInterface] = None, vlan_ids: Set[int] = None):

        if vlan_ids is None:
            vlan_ids = set()

        if interfaces:
            if not all(isinstance(interface, SwitchInterface) for interface in interfaces):
                raise TypeError("Switches only accept connectors of type SwitchInterface()")

        super().__init__(node_id, hostname, x, y, interfaces)
        self.vlans = []
        self.__spanning_tree = True
        self.port_channels = []
        for vlan_id in vlan_ids:
            self.config_vlan(vlan_id)

    def __str__(self):
        return super().__str__().replace("Device", "Switch")

    # VLAN Getter by ID
    def get_vlan(self, vlan_id: int) -> VLAN | None:

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
    def config_vlan(self, vlan_id: int, name: str = None, cidr=None):
        if self.get_vlan(vlan_id):
            self._to_script(self.get_vlan(vlan_id).config(name=name, cidr=cidr))

        else:
            self.vlans.append(VLAN(vlan_id, name, cidr))
            self._to_script(*self.vlans[len(self.vlans) - 1].config())

    # Assigns a VLAN into an interface
    def assign_vlan(self, *vlan_ids: int, ports: str | list | tuple = None, replace: bool = False):
        # Validation
        for vlan_id in vlan_ids:
            if not self.get_vlan(vlan_id):
                raise NotFoundError(f"VLAN {vlan_id} not found")

        if not ports:
            raise ValueError("Missing parameter 'ports': Which of the ports should I assign the VLANs to?")

        # If only one port is assigned, otherwise a list is given
        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            if replace:
                self._to_script(*interface.replace_vlan(*vlan_ids))
            else:
                self._to_script(*interface.assign_vlan(*vlan_ids))

    # Removes a VLAN from an interface
    def detach_vlan(self, vlan_id: int, ports: str | list | tuple = None):
        if not self.get_vlan(vlan_id):
            raise NotFoundError(f"VLAN {vlan_id} not found")

        if not ports:
            raise ValueError("Missing parameter 'ports': Which of the ports should I assign the VLANs to?")

        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            self._to_script(*interface.remove_vlan(vlan_id))

    # Configures the interface as trunk, allowing all VLANs
    def set_default_trunk(self, *ports: str):
        for interface in self.get_ints(*ports):
            self._to_script(*interface.default_trunk())

    # Spanning-tree (Only the basics) =========================================================
    def enable_stp(self):

        if self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already enabled{Style.RESET_ALL}")
        else:
            self.__spanning_tree = True

            self._to_script("spanning-tree vlan 1")
            for vlan in self.vlans:
                self._to_script(f"spanning-tree vlan {vlan.vlan_id}")

    def disable_stp(self):

        if not self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already disabled{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}WARNING: Disabling spanning tree can lead to network loops, broadcast storms, "
                  f"and other issues if not managed carefully.{Style.RESET_ALL}")

            self.__spanning_tree = False

            self._to_script("no spanning-tree vlan 1")
            for vlan in self.vlans:
                self._to_script(f"no spanning-tree vlan {vlan.vlan_id}")

    # Ether-channel =================================================================================
    def create_etherchannel(self, ports: str | list | tuple,
                            port_channel_num: int = None,
                            protocol: Union[Protocol.ECN_LACP, Protocol.ECN_PAGP] = None,
                            unconditional: bool = None):

        if len(ports) <= 1:
            raise ConnectionError("ERROR: One is not enough")

        for interface in self.get_ints(*ports):
            self.get_int(ports[0]).etherchannel_check(interface)
            self._to_script(interface.etherchannel(port_channel_num, protocol, unconditional))
