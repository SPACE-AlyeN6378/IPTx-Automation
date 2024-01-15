from typing import List, Union, Tuple
from components.interfaces.interface import Interface
from colorama import Fore, Style
from enum import Enum


class Mode(Enum):  # ENUM for switchport modes
    NULL = 0
    ACCESS = 1
    TRUNK = 2


class Connector(Interface):
    BANDWIDTHS = {"ATM": 622000, "Ethernet": 10000, "FastEthernet": 100000, "GigabitEthernet": 1000000,
                  "TenGigabitEthernet": 10000000, "Serial": 1544, "wlan-gigabitethernet": 1000000}

    def __init__(self, int_type: str, port: Union[str, int], cidr: str = None, bandwidth: int = None,
                 mtu: int = 1500, duplex: str = "auto") -> None:

        if duplex not in ["auto", "full", "half"]:
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

    def config(self, cidr: str = None, bandwidth: int = None, mtu: int = None,
               duplex: str = None, connect_to=None):
        ios_commands = super().config(cidr)
        exit_ = ios_commands.pop()

        if connect_to:
            self.destination_node = connect_to
            self.shutdown = False

        shutdown_cmd = "shutdown" if self.shutdown else "no shutdown"
        ios_commands.append(shutdown_cmd)

        if mtu:
            self.mtu = mtu
            ios_commands.append(f"mtu {self.mtu}")

        if bandwidth:
            self.bandwidth = bandwidth
            ios_commands.append(f"bandwidth {self.bandwidth}")

        if duplex:
            if duplex not in ["auto", "full", "half"]:
                raise ValueError(f"Inappropriate configuration for duplex \'{duplex}\'")
            
            self.duplex = duplex
            ios_commands.append(f"duplex {self.duplex}")

        ios_commands.append(exit_)
        return ios_commands
    
    def set_shutdown(self, shutdown: bool = True) -> List[str]:
        if not shutdown and not self.destination_node:
            print(f"{Fore.MAGENTA}DENIED: Dangling connector, so it remains shut{Style.RESET_ALL}")
            return []
        else:
            self.shutdown = shutdown
            shutdown_cmd = "shutdown" if self.shutdown else "no shutdown"
            return [
                f"interface {self.int_type}{self.port}",
                shutdown_cmd,
                "exit"
            ]

    def connect_to(self, node) -> List[str]:
        self.destination_node = node
        return self.set_shutdown(False)
    
    def disconnect(self) -> List[str]:
        self.destination_node = None
        return self.set_shutdown(True)

    def __eq__(self, other):
        if isinstance(other, Connector):
            return self.int_type == other.int_type \
                and self.port == other.port \
                and self.ip_address == other.ip_address \
                and self.subnet_mask == other.subnet_mask \
                and self.bandwidth == other.bandwidth \
                and self.mtu == other.mtu \
                and self.duplex == other.duplex \
                and self.destination_node == other.destination_node

        return False
