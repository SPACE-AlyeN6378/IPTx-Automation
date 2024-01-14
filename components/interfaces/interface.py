from __future__ import annotations

import ipaddress
from typing import Union, Tuple, List


class Interface:
    # Interface types with its associated default bandwidths
    DEFAULT_TYPES = ("ATM", "Ethernet", "FastEthernet", "GigabitEthernet", "TenGigabitEthernet",
                     "Serial", "wlan-gigabitethernet", "Loopback", "Tunnel", "VLAN")

    # Split f0/0 --> (FastEthernet, 0/0) from GNS3 =================================================
    @staticmethod
    def split_port_name(shortname: str = "", longname: str = "") -> Tuple[str, str]:

        # Can't accept both
        if shortname and longname:
            raise TypeError("Which parameter do you expect me to use? Please use any one of these two.")

        required_int_type = ""

        # Short name of format, for e.g. g0/1/0
        if shortname:

            for int_type in Interface.DEFAULT_TYPES:
                if int_type[0].lower() == shortname[0].lower():
                    required_int_type = int_type
                    break

            if not required_int_type:
                raise ValueError(f"The initial '{shortname[0]}' is of an invalid interface type")

            required_port = shortname[1:]

        # Long name of format, for e.g. GigabitEthernet0/1/0
        elif longname:
            for int_type in Interface.DEFAULT_TYPES:
                if int_type in longname[:len(int_type)]:
                    required_int_type = int_type
                    break

            if not required_int_type:
                raise ValueError(f"Unacceptable format or invalid interface type '{longname}' - Must be like e.g. "
                                 f"GigabitEthernet0/0/1")

            required_port = longname[len(required_int_type):]

        # If the parameters go missing
        else:
            raise TypeError("Argument missing")

        Interface.is_valid_port(required_port)  # Check if the port number is of the valid port type

        return required_int_type, required_port

    # Gets the IP Address and Subnet mask from CIDR
    @staticmethod
    def get_ip_and_subnet(cidr: str) -> Tuple[Union[str, None], Union[str, None]]:
        if cidr:
            ip_network = ipaddress.IPv4Network(cidr, strict=False)
            ip_address = cidr.split("/")[0]
            subnet_mask = ip_network.netmask
            return ip_address, str(subnet_mask)
        else:
            return None, None

    # To make sure that the port is of the format x or x/x/x/... (x is a number) ===================
    def validate_port(self) -> None:

        if self.int_type in ["Loopback", "Tunnel", "VLAN"]:
            if not isinstance(self.port, int) or self.port < 0:
                raise ValueError(f"Invalid format: '{self.port}' - Please use positive integers")

        else:
            numbers = self.port.split("/")
            if not all(char.isdigit() for char in numbers):
                raise ValueError(f"Invalid format: '{self.port}' - Please use format x/x/..., where x is an integer")

    # Get interface range
    @staticmethod
    def range_(prefix: str | int, numbers: list | tuple | range):
        if not isinstance(prefix, (str, int)):
            raise TypeError("Please use format x/x/... or positive integers")

        if isinstance(prefix, str):
            if not all(char.isdigit() for char in prefix.split("/")):
                raise ValueError(f"Invalid format: '{prefix}' - Please use format x/x/..., where x is an integer")

        if not all(isinstance(number, int) for number in numbers):
            raise ValueError("All numbers should be integers")

        return tuple(f"{prefix}/{number}" for number in numbers)

    # Constructor
    def __init__(self, int_type: str, port: Union[str, int], cidr: str = None) -> None:

        self.int_type = int_type
        self.port = port
        self.ip_address, self.subnet_mask = self.get_ip_and_subnet(cidr)
        self.validate_port()

    # Some operator overloadings
    def __str__(self):
        if self.int_type in ("Loopback", "Tunnel", "VLAN"):
            return f"{self.int_type} {self.port}"
        else:
            return f"{self.int_type}{self.port}"

    def __eq__(self, other):
        if isinstance(other, Interface):
            return self.int_type == other.int_type and self.port == other.port \
                   and self.ip_address == other.ip_address and self.subnet_mask == other.subnet_mask

        return False

    def __contains__(self, item):
        return self.int_type == item.int_type and self.port == item.port \
               and self.ip_address == item.ip_address and self.subnet_mask == item.subnet_mask

    # Configure the interface and generate Cisco command to be sent
    def config(self, cidr: str = None) -> List[str]:
        # Change a couple of attributes
        if cidr:
            self.ip_address, self.subnet_mask = self.get_ip_and_subnet(cidr)

        # Generate cisco command
        ios_commands = []
        if self.int_type in ("Tunnel", "VLAN"):
            ios_commands.append(f"interface {self.int_type} {self.port}")
        else:
            ios_commands.append(f"interface {self.int_type}{self.port}")

        if self.ip_address and self.subnet_mask:
            ios_commands.append(f"ip address {self.ip_address} {self.subnet_mask}")

        ios_commands.append("exit")
        return ios_commands
    
    # Network Address
    def network_address(self):
        ip_address = ipaddress.IPv4Network(f"{self.ip_address}/{self.subnet_mask}", strict=False)
        return ip_address.network_address

    # Wildcard Mask
    def wildcard_mask(self):
        octets = [int(octet) for octet in self.subnet_mask.split('.')]
        wildcard_mask_list = [255 - octet for octet in octets]
        wildcard_mask = '.'.join(map(str, wildcard_mask_list))

        return wildcard_mask

    # Generate Cisco command to advertise OSPF route
    def ospf_advertise(self, area=0):
        if self.ip_address and self.subnet_mask:
            return [f"network {self.network_address()} {self.wildcard_mask()} area {area}"]
        else:
            raise NotImplementedError("The IP address and subnet mask are missing")
