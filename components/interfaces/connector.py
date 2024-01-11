from typing import List, Union, Tuple
from components.interfaces.interface import Interface
from colorama import Fore, Style
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
        self.shutdown = True
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

    def config(self, shutdown: bool = False, cidr: str = None, bandwidth: str = None, mtu: str = None,
               duplex: str = None):
        ios_commands = super().config(cidr)
        exit_ = ios_commands.pop()

        if not shutdown:
            if not self.destination_node:
                print(f"{Fore.YELLOW}REFUSED: Dangling connector, therefore {str(self)} remains shut{Style.RESET_ALL}")
                self.shutdown = True
            else:
                self.shutdown = False
        else:
            self.shutdown = True
        shutdown_cmd = "shutdown" if shutdown else "no shutdown"

        if bandwidth:
            self.bandwidth = bandwidth

        if mtu:
            self.mtu = mtu

        if duplex:
            self.duplex = duplex

        ios_commands.extend([
            shutdown_cmd,
            f"mtu {self.mtu}",
            f"bandwidth {self.bandwidth}",
            f"duplex {self.duplex}"
        ])

        ios_commands.append(exit_)
        return ios_commands

    def connect_to(self, node):
        self.destination_node = node

    def __eq__(self, other):
        if isinstance(other, Connector):
            return self.int_type == other.int_type and self.port == other.port \
                and self.ip_address == other.ip_address and self.subnet_mask == other.subnet_mask \
                and self.destination_node == other.destination_node

        return False
