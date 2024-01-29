from typing import List, Union, Any
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
            raise ValueError(f"ERROR: Inappropriate configuration for duplex \'{duplex}\'")

        super().__init__(int_type, port, cidr)

        self.shutdown_state = True 
        self.bandwidth = bandwidth if bandwidth else Connector.BANDWIDTHS[int_type]
        self.mtu = mtu
        self.duplex = duplex

        # Used when a connection is established, otherwise
        self.remote_device = None      # Connector ID, aka SCR in F@H for router-to-router
        self.remote_port = None

        self._changes_made["shutdown"] = True
        self._changes_made["bandwidth"] = True
        self._changes_made["mtu"] = True
        self._changes_made["duplex"] = True

    # Check if the interface type is actually a connector (e.g. Ethernet)
    def validate_port(self) -> None:
        super().validate_port()

        default_types = Connector.BANDWIDTHS.keys()

        if self.int_type not in default_types:
            raise TypeError(
                f"ERROR: Invalid interface type '{self.int_type}' - Please use the following "
                f"interfaces {', '.join(default_types)}")

    def config(self, cidr: str = None, bandwidth: int = None, mtu: int = None,
               duplex: str = None):
        super().config(cidr)

        if mtu:
            self.mtu = mtu
            self._changes_made["mtu"] = True

        if bandwidth:
            self.bandwidth = bandwidth
            self._changes_made["bandwidth"] = True

        if duplex:
            if duplex not in ["auto", "full", "half"]:
                raise ValueError(f"ERROR: Inappropriate configuration for duplex \'{duplex}\'")
            
            self.duplex = duplex
            self._changes_made["duplex"] = True

    def shutdown(self) -> None:
        if self.shutdown_state:
            print(f"{Fore.MAGENTA}DENIED: This connector is already shut down.{Style.RESET_ALL}")
        else:
            self.shutdown_state = True
            self._changes_made["shutdown"] = True

    def release(self) -> None:
        if not self.shutdown_state:
            print(f"{Fore.MAGENTA}DENIED: This connector has already opened.{Style.RESET_ALL}")
        else:
            if not self.remote_device:
                print(f"{Fore.MAGENTA}DENIED: Dangling connector or not connected, so it remains shut{Style.RESET_ALL}")

            else:
                self.shutdown_state = False
                self._changes_made["shutdown"] = True
            
    def connect_to(self, device: Any, remote_port: int | str) -> None:
        self.remote_device = device
        self.remote_port = remote_port
        self.release()
    
    def disconnect(self) -> None:
        self.remote_device = None
        self.remote_port = None
        self.shutdown()

    def __eq__(self, other):
        if isinstance(other, Connector):
            return self.int_type == other.int_type \
                and self.port == other.port \
                and self.ip_address == other.ip_address \
                and self.subnet_mask == other.subnet_mask \
                and self.bandwidth == other.bandwidth \
                and self.mtu == other.mtu \
                and self.duplex == other.duplex \
                and self.remote_device == other.destination_device

        return False
    
    # Generates a block of commands
    def get_command_block(self):
        ios_commands = [f"interface {self.__str__()}"]
        
        for attr in self._changes_made.keys():
            if self._changes_made[attr]:
                if attr == "shutdown":
                    no = "" if self.shutdown_state else "no "
                    ios_commands.append(f"{no}shutdown")

                elif attr == "ip address":
                    ios_commands.append(f"{attr} {self.ip_address} {self.subnet_mask}")

                elif attr == "bandwidth":
                    ios_commands.append(f"{attr} {self.bandwidth}")

                elif attr == "mtu":
                    ios_commands.append(f"{attr} {self.mtu}")

                elif attr == "duplex":
                    ios_commands.append(f"{attr} {self.duplex}")
                    
                self._changes_made[attr] = False

        if len(ios_commands) > 1:
            ios_commands.append("exit")
            return ios_commands
        
        return []


