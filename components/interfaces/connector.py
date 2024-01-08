from typing import List, Union, Tuple
from components.interfaces.interface import Interface
from enum import Enum


class Mode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2


class Duplex(Enum):
    AUTO = "auto"
    FULL = "full"
    HALF = "half"


class Connector(Interface):
    BANDWIDTHS = {"ATM": 622000, "Ethernet": 10000, "FastEthernet": 100000, "GigabitEthernet": 1000000,
                  "TenGigabitEthernet": 10000000, "Serial": 1544, "wlan-gigabitethernet": 1000000}

    def __init__(self, int_type: str, port: Union[str, int], cidr: str = None, bandwidth: int = None,
                 mtu: int = 1500, duplex: str = Duplex.AUTO) -> None:

        super().__init__(int_type, port, cidr)
        self.bandwidth = bandwidth if bandwidth else Connector.BANDWIDTHS[int_type]
        self.mtu = mtu
        self.duplex = duplex
        self.destination_node = None

        self.vlans = set()
        self.__switchport_mode = Mode.NULL

    # Check if the interface type is actually a connector (e.g. Ethernet)
    def validate_port(self) -> None:
        super().validate_port()

        default_types = Connector.BANDWIDTHS.keys()

        if self.int_type not in default_types:
            raise TypeError(
                f"Invalid interface type '{self.int_type}' - Please use the following interfaces {', '.join(default_types)}")

    def config(self, cidr: str = None, bandwidth: str = None, mtu: str = None, generate_cmd=True):
        cisco_commands = super().config(cidr, generate_cmd)

        if bandwidth:
            self.bandwidth = bandwidth

        if mtu:
            self.mtu = mtu

        if cisco_commands:
            cisco_commands.append("no shutdown")
            cisco_commands.append(f"mtu {self.mtu}")
            cisco_commands.append(f"bandwidth {self.bandwidth}")

        return cisco_commands

    def connect_to(self, node):
        self.destination_node = node

    # VLAN Functions
    def __access_command(self) -> List[str]:
        ios_commands = []

        if len(self.vlans) == 1:
            if self.__switchport_mode != Mode.ACCESS:
                self.__switchport_mode = Mode.ACCESS

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
            self.__switchport_mode = Mode.NULL

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

        if not vlan_ids:
            raise ValueError("Missing parameters for VLAN IDs")

        if self.__switchport_mode != Mode.TRUNK:
            self.__switchport_mode = Mode.TRUNK

            ios_commands = [
                f"interface {self.int_type}{self.port}",
                "switchport encapsulation dot1q",
                # switchport trunk native vlan <native_vlan_id>
                f"switchport trunk allowed vlan {','.join(str(vlan_id) for vlan_id in self.vlans)}",
                "switchport mode trunk",
                "switchport nonegotiate",
                "exit"
            ]

        else:
            ios_commands = [
                f"interface {self.int_type}{self.port}",
                # switchport trunk native vlan <native_vlan_id>
                f"switchport trunk allowed vlan add {','.join(str(vlan_id) for vlan_id in vlan_ids)}",
                "exit"
            ]

        return ios_commands

    def __trunk_replace_command(self, *vlan_ids: int) -> List[str]:

        ios_commands = [
            f"interface {self.int_type}{self.port}",
            f"switchport trunk allowed vlan {','.join(str(vlan_id) for vlan_id in vlan_ids)}",
            "exit"
        ]

        if self.__switchport_mode != Mode.TRUNK:
            self.__switchport_mode = Mode.TRUNK
            ios_commands.insert(1, "switchport encapsulation dot1q")
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

    def assign_vlan(self, *vlan_ids: int, trunking: bool = False) -> List[str]:
        # No empty parameters
        if not vlan_ids:
            raise ValueError("Missing parameters for VLAN IDs")
        # All VLAN IDs must be an integer
        if any(not isinstance(vlan_id, int) for vlan_id in vlan_ids):
            raise TypeError("All VLAN IDs must be an integer")

        for vlan_id in vlan_ids:
            self.vlans.add(vlan_id)

        if len(self.vlans) > 1 or trunking:  # Multiple VLANs
            return self.__trunk_command(*vlan_ids)
        else:
            return self.__access_command()

    def replace_vlan(self, *vlan_ids: int, trunking: bool = False) -> List[str]:
        # No empty parameters
        if not vlan_ids:
            raise ValueError("Missing parameters for VLAN IDs")
        # All VLAN IDs must be an integer
        if any(not isinstance(vlan_id, int) for vlan_id in vlan_ids):
            raise TypeError("All VLAN IDs must be an integer")

        self.vlans = set(vlan_ids)

        if len(self.vlans) > 1 or trunking:  # Multiple VLANs
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

# More features:
#   - Port security
