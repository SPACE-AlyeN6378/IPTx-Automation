from __future__ import annotations

from components.nodes.network_device import NetworkDevice
from components.interfaces.vlan import VLAN
from components.nodes.notfound_error import NotFoundError
from typing import List, Union, Set, Tuple, Iterable
from enum import Enum
from colorama import Fore, Style

from components.interfaces.connector import Connector

from list_helper import merge_list


class SwitchMode(Enum):  # ENUM for switchport modes
    ACCESS = 1
    TRUNK = 2
    DOT1Q_TUNNEL = 3


class ECNProtocol(Enum):
    PAGP = 4
    LACP = 5


class SwitchInterface(Connector):
    def __init__(self, int_type: str, port: str | int, cidr: str = None, bandwidth: int = None, mtu: int = 1500,
                 duplex: str = "auto") -> None:

        super().__init__(int_type, port, cidr, bandwidth, mtu, duplex)
        self.vlan_ids = set()
        self.__switchport_mode = None
        self.dtp_enabled = True

        # Etherchannel
        self.port_channel = 0
        self.ecn_protocol = None
        self.unconditional = True

        # Switchport command
        self.__switchport_cmd = []
        self.__channel_group_cmd = ""

    # VLAN Functions
    def __access_command(self) -> None:
        ios_commands = []

        if len(self.vlan_ids) == 1:

            ios_commands = [
                f"switchport access vlan {list(self.vlan_ids)[0]}"
            ]

            if self.__switchport_mode != SwitchMode.ACCESS:
                self.__switchport_mode = SwitchMode.ACCESS
                ios_commands.insert(0, "switchport mode access")

            if self.dtp_enabled:
                ios_commands.append("switchport nonegotiate")
                self.dtp_enabled = False

        else:
            print(f"{Fore.MAGENTA}DENIED: This connector should hold only one VLAN{Style.RESET_ALL}")

        self.__switchport_cmd.clear()
        self.__switchport_cmd.extend(ios_commands)

    def __disable_both_command(self) -> None:
        ios_commands = []

        # For this command to work, the VLAN ID list must be empty
        if not self.vlan_ids:
            self.__switchport_mode = None

            ios_commands = [
                "no switchport mode trunk",
                "no switchport mode access"
            ]
        else:
            print(f"{Fore.MAGENTA}DENIED: Non-empty VLAN list{Style.RESET_ALL}")

        self.__switchport_cmd.clear()
        self.__switchport_cmd.extend(ios_commands)

    def __trunk_add_command(self, *vlan_ids: int) -> None:

        ios_commands = []

        if self.__switchport_mode != SwitchMode.TRUNK:
            self.__switchport_mode = SwitchMode.TRUNK

            ios_commands = [
                "switchport trunk encapsulation dot1q",
                # switchport trunk native vlan <native_vlan_id>
                "switchport mode trunk"
            ]
            if vlan_ids:
                ios_commands.append(f"switchport trunk allowed vlan"
                                    f" {','.join(str(vlan_id) for vlan_id in self.vlan_ids)}")

        elif vlan_ids:
            ios_commands = [
                # switchport trunk native vlan <native_vlan_id>
                f"switchport trunk allowed vlan add {','.join(str(vlan_id) for vlan_id in vlan_ids)}",
            ]

        if self.dtp_enabled:
            ios_commands.append("switchport nonegotiate")
            self.dtp_enabled = False

        self.__switchport_cmd.extend(ios_commands)

    def __trunk_replace_command(self, *vlan_ids: int) -> None:

        ios_commands = []

        if vlan_ids:
            ios_commands.append(f"switchport trunk allowed vlan "
                                f"{','.join(str(vlan_id) for vlan_id in vlan_ids)}")

        if self.__switchport_mode != SwitchMode.TRUNK:
            self.__switchport_mode = SwitchMode.TRUNK
            ios_commands.insert(0, "switchport trunk encapsulation dot1q")
            ios_commands.append("switchport mode trunk")

        self.__switchport_cmd.extend(ios_commands)

    def __trunk_remove_command(self, vlan_id: int) -> None:
        if self.__switchport_mode != SwitchMode.TRUNK:
            raise ConnectionError("This connector is not in switchport trunk mode")

        self.__switchport_cmd.append(f"switchport trunk allowed vlan remove {vlan_id}")

    def __dot1q_tunnel_command(self):
        ios_commands = [
            f"switchport access vlan {list(self.vlan_ids)[0]}",
            "switchport mode dot1q-tunnel"
        ]

        if self.dtp_enabled:
            ios_commands.append("switchport nonegotiate")
            self.dtp_enabled = False

        self.__switchport_cmd.extend(ios_commands)

    # These VLAN assignment functions will be used outside the class structure ===================================
    def assign_vlan(self, *vlan_ids: int) -> None:

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
            self.__trunk_add_command(*vlan_ids)
        else:
            self.__access_command()

    def replace_vlan(self, *vlan_ids: int) -> None:
        # No empty parameters
        if not vlan_ids:
            raise ValueError("Missing parameters for VLAN IDs")
        # All VLAN IDs must be an integer
        if any(not isinstance(vlan_id, int) for vlan_id in vlan_ids):
            raise TypeError("All VLAN IDs must be an integer")

        self.vlan_ids = set(vlan_ids)

        if len(self.vlan_ids) > 1 or isinstance(self.destination_device, Switch):  # Multiple VLANs
            self.__trunk_replace_command(*vlan_ids)
        else:
            self.__access_command()

    def remove_vlan(self, vlan_id: int) -> None:

        if not isinstance(vlan_id, int):
            raise TypeError("VLAN ID must be an integer")

        self.vlan_ids.discard(vlan_id)

        if len(self.vlan_ids) > 1 or isinstance(self.destination_device, Switch):  # Multiple VLANs
            self.__trunk_remove_command(vlan_id)
        elif len(self.vlan_ids) == 1:
            self.__access_command()
        else:
            self.__switchport_mode = None
            if isinstance(self.destination_device, Switch):
                self.__trunk_add_command()
            else:
                self.__disable_both_command()

    # Configure switchport as trunk for all VLANs 1-4094
    def default_trunk(self):
        self.__switchport_mode = None
        self.vlan_ids.clear()
        self.__trunk_add_command()

    def dot1q_tunnel(self, vlan_id: int):
        self.vlan_ids = {vlan_id}
        self.__switchport_mode = SwitchMode.DOT1Q_TUNNEL

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

    def etherchannel(self, port_channel_num: int,
                     protocol: Union[ECNProtocol.LACP, ECNProtocol.PAGP] = None,
                     unconditional: bool = None) -> None:

        # Check for any errors in connection
        if self.destination_device is None:
            raise ConnectionError(f"ERROR: Dangling connector or unconnected {self.int_type}{self.port}")

        if not isinstance(self.destination_device, Switch):
            raise TypeError("ERROR: Ether-channels only supports switches in this backbone network")

        self.port_channel = port_channel_num

        if protocol not in [ECNProtocol.LACP, ECNProtocol.PAGP, None]:
            raise ValueError("ERROR: Incorrect protocols. Ether-channels either use PAgP, LACP, or None")

        self.ecn_protocol = protocol

        if unconditional is not None:
            self.unconditional = unconditional

        # Generate cisco command
        protocol_keyword = ""
        if self.ecn_protocol == ECNProtocol.LACP:
            if self.unconditional:
                protocol_keyword = "active"
            else:
                protocol_keyword = "passive"

        elif self.ecn_protocol == ECNProtocol.PAGP:
            if self.unconditional:
                protocol_keyword = "desirable"
            else:
                protocol_keyword = "auto"
    
        else:
            protocol_keyword = "on"

        self.__channel_group_cmd = f"channel-group {self.port_channel} mode {protocol_keyword}"

    def get_command_block(self):
        commands = super().get_command_block()

        if self.__channel_group_cmd:
            self.__switchport_cmd.append(self.__channel_group_cmd)

        if self.__switchport_cmd:
            if not commands:
                commands.append(f"interface {self.__str__()}")
                commands.extend(self.__switchport_cmd)
                commands.append("exit")

            else:
                exit_ = commands.pop()
                commands.extend(self.__switchport_cmd)
                commands.append(exit_)

        self.__channel_group_cmd = ""
        self.__switchport_cmd.clear()

        return commands


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


class Switch(NetworkDevice):

    def __init__(self, node_id: str | int, hostname: str = "Switch", x: int = 0, y: int = 0,
                 interfaces: Iterable[SwitchInterface] = None, vlan_ids: Set[int] = None):

        if vlan_ids is None:
            vlan_ids = set()

        if interfaces:
            if not all(isinstance(interface, SwitchInterface) for interface in interfaces):
                raise TypeError("Switches only accept connectors of type SwitchInterface()")
            
        self.vlan_config_cmds = []
        self.stp_config_cmds = []
        self.etherchannel_config_cmds = []

        super().__init__(node_id, hostname, x, y, interfaces)
        self.vlans = []
        self.__spanning_tree = True
        self.port_channels = set()
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
    def config_vlan(self, vlan_id: int, name: str = None, cidr=None) -> None:
        if self.get_vlan(vlan_id):
            self.vlan_config_cmds.extend(self.get_vlan(vlan_id).config(name=name, cidr=cidr))

        else:
            self.vlans.append(VLAN(vlan_id, name, cidr))
            self.vlan_config_cmds.extend(self.vlans[len(self.vlans) - 1].config())

    # Assigns a VLAN into an interface
    def assign_vlan(self, *vlan_ids: int, ports: str | Iterable[str] = None, replace: bool = False) -> None:
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
                interface.replace_vlan(*vlan_ids)
            else:
                interface.assign_vlan(*vlan_ids)

    # Removes a VLAN from an interface
    def detach_vlan(self, vlan_id: int, ports: str | Iterable[str] = None) -> None:
        if not self.get_vlan(vlan_id):
            raise NotFoundError(f"VLAN {vlan_id} not found")

        if not ports:
            raise ValueError("Missing parameter 'ports': Which of the ports should I assign the VLANs to?")

        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            interface.remove_vlan(vlan_id)

    # Configures the interface as trunk, allowing all VLANs
    def set_default_trunk(self, *ports: str):
        for interface in self.get_ints(*ports):
            interface.default_trunk()

    # Spanning-tree (Only the basics) =========================================================
    def enable_stp(self):

        if self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already enabled{Style.RESET_ALL}")
        else:
            self.__spanning_tree = True

            self.stp_config_cmds.append("spanning-tree vlan 1")
            for vlan in self.vlans:
                self.stp_config_cmds.append(f"spanning-tree vlan {vlan.vlan_id}")

    def disable_stp(self):

        if not self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already disabled{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}WARNING: Disabling spanning tree can lead to network loops, broadcast storms, "
                  f"and other issues if not managed carefully.{Style.RESET_ALL}")

            self.__spanning_tree = False

            self.stp_config_cmds.append("no spanning-tree vlan 1")
            for vlan in self.vlans:
                self.stp_config_cmds.append(f"no spanning-tree vlan {vlan.vlan_id}")

    # Ether-channel =================================================================================
    def create_etherchannel(self, ports: str | list | tuple,
                            port_channel_num: int = None,
                            protocol: Union[ECNProtocol.ECN_LACP, ECNProtocol.ECN_PAGP] = None,
                            unconditional: bool = None):

        if len(ports) <= 1:
            raise ConnectionRefusedError("ERROR in etherchannel: One is not enough")
        
        if port_channel_num in self.port_channels:
            raise ConnectionRefusedError(f"ERROR in etherchannel: Port channel number {port_channel_num} already exists")
        
        self.port_channels.add(port_channel_num)

        for interface in self.get_ints(*ports):
            self.get_int(ports[0]).etherchannel_check(interface)
            interface.etherchannel(port_channel_num, protocol, unconditional)

    def submit_script(self):
        script = super().submit_script()
        script.insert(1, self.vlan_config_cmds)
        script.insert(2, self.stp_config_cmds)
        merge_list(script)

        NetworkDevice.print_script(commands=script, color=Fore.CYAN)

        # pyperclip.copy("\n".join(script) + "\n")  # This will be replaced with netmiko soon
        self.vlan_config_cmds.clear()
        self.stp_config_cmds.clear()
        self.etherchannel_config_cmds.clear()
        return script

