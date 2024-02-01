from __future__ import annotations
from components.nodes.network_device import NetworkDevice
from components.interfaces.vlan import VLAN
from components.nodes.notfound_error import NotFoundError
from typing import Union, Set, Iterable, List
from enum import Enum
from colorama import Fore, Style
from iptx_utils import SwitchportError

from components.interfaces.physical_interface import PhysicalInterface

from list_helper import list_to_str, replace_key


class Mode(Enum):  # ENUM for switchport modes
    ACCESS = 1
    TRUNK = 2
    DOT1Q_TUNNEL = 3


class ECNProtocol(Enum):
    PAGP = 4
    LACP = 5


class SwitchInterface(PhysicalInterface):
    def __init__(self, int_type: str, port: str | int, cidr: str = None) -> None:

        super().__init__(int_type, port, cidr)
        self.vlan_ids = set()
        self.__switchport_mode = None
        self.__dtp_enabled = True
        self.__stp_bpdu_filter = True

        # Etherchannel
        self.port_channel = 0
        self.ecn_protocol = None
        self.unconditional = True

        # Switchport command
        self.__switchport_cmd = []
        self.__channel_group_cmd = []
        self.__stp_cmd = ["spanning-tree bpdufilter enable"]

    def set_vlans(self, mode: Mode.ACCESS | Mode.TRUNK | Mode.DOT1Q_TUNNEL = None,
                  vlan_ids: int | Iterable[int] = None,
                  replace: bool = False):

        # Set switchport mode
        if mode:
            if mode not in [Mode.ACCESS, Mode.TRUNK, Mode.DOT1Q_TUNNEL]:
                raise SwitchportError(
                    f"ERROR: Unacceptable switchport '{mode}'. Accepted switchport modes are "
                    f"ACCESS, TRUNK, and DOT1Q_TUNNEL")

            self.__switchport_mode = mode

            if self.__switchport_mode == Mode.ACCESS:
                self.__switchport_cmd.append("switchport mode access")
            elif self.__switchport_mode == Mode.TRUNK:
                self.__switchport_cmd.extend(["switchport trunk encapsulation dot1q", "switchport mode trunk"])
            elif self.__switchport_mode == Mode.DOT1Q_TUNNEL:
                self.__switchport_cmd.append("switchport mode dot1q-tunnel")

        # Set or replace the VLAN IDs
        if vlan_ids:
            if not self.__switchport_mode:
                raise SwitchportError("ERROR: The switchport mode is neither in ACCESS, TRUNK nor DOT1Q_TUNNEL")

            if not isinstance(vlan_ids, Iterable):
                vlan_ids = [vlan_ids]

            if replace:
                self.vlan_ids = set(vlan_ids)
            else:
                self.vlan_ids = self.vlan_ids | set(vlan_ids)

        # Generate commands
        if self.__switchport_mode in {Mode.ACCESS, Mode.DOT1Q_TUNNEL}:
            # When more than one VLANs are contained
            if len(self.vlan_ids) > 1:
                print(f"{Fore.YELLOW}WARNING: There are more than one VLAN IDs in "
                      f"interface {str(self)} '{str(self.vlan_ids)}'.")

                if vlan_ids:
                    print(f"Using VLAN {vlan_ids[0]} in the parameter...{Style.RESET_ALL}")
                    self.vlan_ids = {vlan_ids[0]}
                else:
                    print(f"Using VLAN {list(self.vlan_ids)[0]} in the properties...{Style.RESET_ALL}")
                    self.vlan_ids = {list(self.vlan_ids)[0]}

            self.__switchport_cmd.append(f"switchport access vlan {list(self.vlan_ids)[0]}")

        elif self.__switchport_mode == Mode.TRUNK:
            self.__switchport_cmd.append(f"switchport trunk allowed vlan {list_to_str(self.vlan_ids)}")

        # If auto-negotiation is enabled, it gets disabled
        if self.__dtp_enabled:
            self.__switchport_cmd.append("switchport nonegotiate")
            self.__dtp_enabled = False

    def remove_vlan(self, vlan_id: int):
        self.vlan_ids.discard(vlan_id)

        if self.__switchport_mode in {Mode.ACCESS, Mode.DOT1Q_TUNNEL}:
            self.__switchport_cmd.append(f"no switchport access vlan {vlan_id}")

        elif self.__switchport_mode == Mode.TRUNK:
            self.__switchport_cmd.append(f"switchport trunk allowed vlan remove {vlan_id}")

    def reset_switchport(self):

        if self.port_channel != 0:
            raise SwitchportError(
                f"ERROR in {str(self)}: Configured as etherchannel, so cannot reset switchport.\n"
                f"Please remove etherchannel first.")

        if self.__switchport_mode == Mode.ACCESS:
            self.__switchport_cmd.extend([
                "no switchport mode access",
                f"no switchport access vlan {list(self.vlan_ids)[0]}"
            ])

        elif self.__switchport_mode == Mode.DOT1Q_TUNNEL:
            self.__switchport_cmd.extend([
                "no switchport mode dot1q-tunnel",
                f"no switchport access vlan {list(self.vlan_ids)[0]}"
            ])

        elif self.__switchport_mode == Mode.TRUNK:
            self.__switchport_cmd.extend([
                "no switchport trunk encapsulation dot1q",
                f"no switchport trunk allowed vlan {list_to_str(self.vlan_ids)}",
                "no switchport mode trunk"
            ])

        self.__switchport_mode = None
        self.vlan_ids.clear()

    # Configure switchport as trunk for all VLANs 1-4094
    def trunk_default(self):
        self.reset_switchport()
        self.set_vlans(mode=Mode.TRUNK)

    # Check if establishing ether-channels fulfills the required criteria
    def etherchannel_check(self, other: SwitchInterface):
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
        # Unused port channels
        elif self.port_channel != other.port_channel:
            raise ConnectionError(
                f"ERROR in {str(self)}: The other interface is configured "
                f"with another port channel, {other.port_channel}")
        # Switchport
        elif self.__switchport_mode != other.__switchport_mode:
            raise ValueError(f"ERROR: Mismatching switchport modes")
        # Same VLANs
        elif self.vlan_ids != other.vlan_ids:
            raise ValueError(f"ERROR: Mismatching VLAN IDs")
        # Same remote device
        elif self.remote_device != other.remote_device:
            raise ConnectionError(f"ERROR: Not connected to the same device")

    def set_stp_bpdu_filter(self, enable: bool = True) -> None:
        self.__stp_bpdu_filter = enable
        no_ = "" if enable else "no "

        if self.__stp_cmd:
            self.__stp_cmd.clear()
        self.__stp_cmd.append(f"{no_}spanning-tree bpdufilter enable")

    @staticmethod
    def generate_eth_cmd(port_channel_num, protocol, unconditional):
        # Generate cisco command
        if protocol == ECNProtocol.LACP:
            protocol_keyword = "active" if unconditional else "passive"

        elif protocol == ECNProtocol.PAGP:
            protocol_keyword = "desirable" if unconditional else "auto"

        else:
            protocol_keyword = "on"

        return f"channel-group {port_channel_num} mode {protocol_keyword}"

    # Configure as etherchannel
    def etherchannel(self, port_channel_num: int,
                     protocol: Union[ECNProtocol.LACP, ECNProtocol.PAGP] = None,
                     unconditional: bool = None) -> None:

        # Check for any errors
        if self.remote_device is None:
            raise ConnectionError(f"ERROR in {str(self)}: Dangling connector or unconnected port")

        if not isinstance(self.remote_device, Switch):
            raise TypeError(f"ERROR in {str(self)}: Ether-channels only supports switches in this backbone network")

        if protocol not in [ECNProtocol.LACP, ECNProtocol.PAGP, None]:
            raise ValueError(
                f"ERROR in {str(self)}: Incorrect protocols. Ether-channels either use PAgP, LACP, or None")

        if not self.__switchport_mode:
            self.trunk_default()

        # Make some settings
        if self.port_channel != 0:
            self.__channel_group_cmd.append(f"no channel-group {self.port_channel}")

        self.port_channel = port_channel_num
        self.ecn_protocol = protocol

        if unconditional is not None:
            self.unconditional = unconditional

        self.__channel_group_cmd.append(
            SwitchInterface.generate_eth_cmd(self.port_channel, self.ecn_protocol, self.unconditional))

    def remove_etherchannel(self):
        if not self.port_channel:
            raise SwitchportError(f"ERROR in {str(self)}: Etherchannel not configured yet")

        self.__channel_group_cmd.append(f"no channel-group {self.port_channel}")
        self.port_channel = 0
        self.ecn_protocol = None

    def get_command_block(self):
        commands = super().get_command_block()

        if self.__switchport_cmd:

            if not commands:
                commands.append(f"interface {self.__str__()}")
                commands.extend(self.__switchport_cmd)
                commands.append("exit")

            else:
                exit_ = commands.pop()
                commands.extend(self.__switchport_cmd)
                commands.append(exit_)

        commands[-1:-1] = self.__channel_group_cmd
        commands[-1:-1] = self.__stp_cmd

        self.__channel_group_cmd.clear()
        self.__switchport_cmd.clear()

        return commands




# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


class Switch(NetworkDevice):

    def __init__(self, node_id: str | int = None, hostname: str = "Switch", x: int = 0, y: int = 0,
                 interfaces: Iterable[SwitchInterface] = None, vlan_ids: Set[int] = None):

        if vlan_ids is None:
            vlan_ids = set()

        if interfaces:
            if not all(isinstance(interface, SwitchInterface) for interface in interfaces):
                raise TypeError("Switches only accept connectors of type SwitchInterface()")

        self.vlan_config_cmds = []
        self.stp_config_cmds = []
        self.port_channel_cmds = []
        self.etherchannel_config_cmds = []

        super().__init__(node_id, hostname, x, y, interfaces)
        self.vlans = []
        self.__spanning_tree = True
        self.port_channels = dict()
        for vlan_id in vlan_ids:
            self.config_vlan(vlan_id)

    def __str__(self):
        return super().__str__().replace("Device", "SW")

    # VLAN Getter by ID
    def get_vlan(self, vlan_id: int) -> VLAN | None:

        for vlan in self.vlans:
            if vlan.vlan_id == vlan_id:
                return vlan

        return None

    def __getitem__(self, port: str) -> SwitchInterface:
        return self.interfaces[port]

    def get_ints(self, *ports: str) -> list[SwitchInterface]:
        data: list[SwitchInterface] = [item for item in super().get_ints(*ports) if isinstance(item, SwitchInterface)]
        return data

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
    def assign_vlans(self, *vlan_ids: int, ports: str | Iterable[str] = None, trunking_only: bool = False,
                     replace: bool = False) -> None:
        # Check if one of those VLANs exist
        for vlan_id in vlan_ids:
            if not self.get_vlan(vlan_id):
                raise NotFoundError(f"VLAN {vlan_id} not found")

        if not ports:
            raise ValueError(
                f"ERROR in switch {self.hostname}: Missing parameter 'ports': Which of the ports should I assign the "
                f"VLANs to?")

        # If only one port is assigned, otherwise a list is given
        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            if len(interface.vlan_ids) < 1 and len(vlan_ids) <= 1 and not trunking_only:
                interface.set_vlans(Mode.ACCESS, vlan_ids, replace)
            else:
                interface.set_vlans(Mode.TRUNK, vlan_ids, replace)

    # Removes a VLAN from an interface
    def withdraw_vlan(self, vlan_id: int, ports: str | Iterable[str] = None) -> None:
        if not self.get_vlan(vlan_id):
            raise NotFoundError(f"ERROR in switch {self.hostname}: VLAN {vlan_id} not found")

        if not ports:
            raise ValueError(
                f"ERROR in switch {self.hostname}! Missing parameter 'ports': Which of the ports should I assign the "
                f"VLANs to?")

        ports = [ports] if isinstance(ports, str) else ports

        for interface in self.get_ints(*ports):
            interface.remove_vlan(vlan_id)

    # Configures the interface as trunk, allowing all VLANs
    def set_default_trunk(self, *ports: str):
        for interface in self.get_ints(*ports):
            interface.trunk_default()

    def reset_switchport(self, *ports: str):
        for interface in self.get_ints(*ports):
            interface.reset_switchport()

    # Spanning-tree (Only the basics) =========================================================
    def enable_stp(self):

        if self.__spanning_tree:
            print(f"{Fore.MAGENTA}DENIED: The Spanning-tree Protocol is already enabled{Style.RESET_ALL}")
        else:
            self.__spanning_tree = True
            for interface in self.interfaces:
                interface.set_stp_bpdu_filter(True)

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
            for interface in self.interfaces:
                interface.set_stp_bpdu_filter(False)

            self.stp_config_cmds.append("no spanning-tree vlan 1")
            for vlan in self.vlans:
                self.stp_config_cmds.append(f"no spanning-tree vlan {vlan.vlan_id}")

    # Ether-channel =================================================================================
    def etherchannel(self, ports: List[str] | tuple[str],
                     port_channel_num: int = None,
                     protocol: Union[ECNProtocol.LACP, ECNProtocol.PAGP] = None,
                     unconditional: bool = None):

        if len(ports) <= 1:
            raise ConnectionRefusedError(
                f"ERROR in switch {self.hostname}: One is not enough for the etherchannel to be established")

        if ports in self.port_channels.values():
            self.etherchannel_config_cmds.extend([
                f"interface Port-channel {port_channel_num}",
                SwitchInterface.__generate_eth_cmd(port_channel_num, protocol, unconditional),
                "exit"
            ])
            replace_key(self.port_channels, ports, port_channel_num)
        else:
            if port_channel_num in self.port_channels.keys():
                self.remove_etherchannel(port_channel_num)
            self.port_channels[port_channel_num] = ports

        # Validation
        for interface in self.get_ints(*ports):
            interface.etherchannel_check(self[ports[0]])

        # Configure the interfaces
        for interface in self.get_ints(*ports):
            interface.etherchannel(port_channel_num, protocol, unconditional)

    def remove_etherchannel(self, port_channel_num: int):

        ports = self.port_channels[port_channel_num]
        self.etherchannel_config_cmds.extend([
            f"no interface Port-channel {port_channel_num}",
        ])

        for interface in self.get_ints(*ports):
            interface.remove_etherchannel()

    # Send script to the actual switch =================================================================================
    def send_script(self, print_to_console: bool = True):
        script = super().send_script()
        more_commands = self.vlan_config_cmds + self.stp_config_cmds + self.etherchannel_config_cmds
        script[1:1] = more_commands

        if print_to_console:
            NetworkDevice.print_script(commands=script, color=Fore.CYAN)

        # pyperclip.copy("\n".join(script) + "\n")  # This will be replaced with netmiko soon
        self.vlan_config_cmds.clear()
        self.stp_config_cmds.clear()
        self.etherchannel_config_cmds.clear()
        return script
