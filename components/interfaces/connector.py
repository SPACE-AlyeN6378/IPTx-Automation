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

        if duplex not in [Duplex.AUTO, Duplex.FULL, Duplex.HALF]:
            raise ValueError(f"Inappropriate configuration for duplex \'{duplex}\'")

        super().__init__(int_type, port, cidr)
        self.bandwidth = bandwidth if bandwidth else Connector.BANDWIDTHS[int_type]
        self.mtu = mtu
        self.duplex = duplex
        self.destination_node = None

    # Check if the interface type is actually a connector (e.g. Ethernet)
    def validate_port(self) -> None:
        super().validate_port()

        default_types = Connector.BANDWIDTHS.keys()

        if self.int_type not in default_types:
            raise TypeError(
                f"Invalid interface type '{self.int_type}' - Please use the following "
                f"interfaces {', '.join(default_types)}")

    def config(self, cidr: str = None, bandwidth: str = None, mtu: str = None, duplex: str = None):
        ios_commands = super().config(cidr)
        exit = ios_commands.pop()

        if bandwidth:
            self.bandwidth = bandwidth

        if mtu:
            self.mtu = mtu

        if duplex:
            self.duplex = duplex

        ios_commands.extend([
            "no shutdown",
            f"mtu {self.mtu}",
            f"bandwidth {self.bandwidth}",
            f"duplex {self.duplex}"
        ])

        ios_commands.append(exit)
        return ios_commands

    def connect_to(self, node):
        self.destination_node = node
