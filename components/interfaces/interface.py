from __future__ import annotations

import ipaddress
from ipaddress import IPv4Address
from typing import Union, Tuple, List, Iterable


class Interface:
    # Interface types with its associated default bandwidths
    DEFAULT_TYPES = ("ATM", "Ethernet", "FastEthernet", "GigabitEthernet", "TenGigabitEthernet",
                     "Serial", "wlan-gigabitethernet", "Loopback", "Tunnel", "VLAN")

    # Gets the IP Address and Subnet mask from CIDR
    @staticmethod
    def get_ip_and_subnet(cidr: str) -> Tuple[str | None, str | None]:
        if cidr:
            ip_network = ipaddress.IPv4Network(cidr, strict=False)
            ip_address = cidr.split("/")[0]
            subnet_mask = ip_network.netmask
            return ip_address, str(subnet_mask)
        else:
            return None, None

    @staticmethod
    def consistent_spacing_ip(ip_address: str = None) -> str | None:
        if ip_address is not None:
            octets = list(map(int, ip_address.split(".")))
            octets = [f"{octet:3d}" for octet in octets]
            return '.'.join(octets)

        return '               '

    # To make sure that the port is of the format x or x/x/x/... (x is a number) ===================
    @staticmethod
    def validate_port(int_type: str, port: str | int) -> None:

        if int_type in ["Loopback", "Tunnel", "VLAN"]:
            if not isinstance(port, int) or port < 0:
                raise ValueError(f"Invalid format: '{port}' - Please use positive integers")

        else:
            numbers = port.split("/")
            if not all(char.isdigit() for char in numbers):
                raise ValueError(f"Invalid format: '{port}' - Please use format x/x/..., where x is an integer")

    # Get interface range
    @staticmethod
    def range(prefix: str | int, numbers: Iterable[int]):
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
        self.description = ""
        Interface.validate_port(self.int_type, self.port)  # Check if the port number is of the valid format

        # Cisco IOS commands
        self._cisco_commands = {
            "ip address": [],
            "description": []
        }

        if self.ip_address is not None:
            self._cisco_commands["ip address"].append(f"ip address {self.ip_address} {self.subnet_mask}")

    # Stringify
    def __str__(self):
        if self.int_type in ("Tunnel", "VLAN"):
            return f"{self.int_type} {self.port}"
        else:
            return f"{self.int_type}{self.port}"

    # Equality (for identification)
    def __eq__(self, other):
        if isinstance(other, Interface):
            return self.int_type == other.int_type and self.port == other.port \
                and self.ip_address == other.ip_address and self.subnet_mask == other.subnet_mask

        return False

    def __contains__(self, item):
        return self.int_type == item.int_type and self.port == item.port \
            and self.ip_address == item.ip_address and self.subnet_mask == item.subnet_mask

    # Configure the interface and generate Cisco command to be sent
    def config(self, cidr: str = None, description: str = None) -> None:
        # Change a couple of attributes
        if cidr:
            self.ip_address, self.subnet_mask = Interface.get_ip_and_subnet(cidr)

            # Generate cisco command
            self._cisco_commands["ip address"] = [f"ip address {self.ip_address} {self.subnet_mask}"]

        if description:
            self.description = description
            self._cisco_commands["description"] = [f"description \"{self.description}\""]

    # Network Address
    def network_address(self) -> IPv4Address:
        ip_address = ipaddress.IPv4Network(f"{self.ip_address}/{self.subnet_mask}", strict=False)
        return ip_address.network_address

    # Wildcard Mask
    def wildcard_mask(self) -> str:
        octets = [int(octet) for octet in self.subnet_mask.split('.')]
        wildcard_mask_list = [255 - octet for octet in octets]
        wildcard_mask = '.'.join(map(str, wildcard_mask_list))

        return wildcard_mask

    # Generate Cisco command to advertise OSPF route
    # Goes to router interface

    # Generates a block of commands
    def generate_command_block(self):
        # Gets a new list of commands
        command_block = [f"interface {str(self)}"]

        for attr in self._cisco_commands.keys():
            # Check if each line of the command exists
            if self._cisco_commands[attr]:
                # Add to command_block and clear the string
                command_block.extend(self._cisco_commands[attr])
                self._cisco_commands[attr].clear()

        # If the generated command exists, return the full list of commands, otherwise return an empty list
        if len(command_block) > 1:
            command_block.append("exit")
            return command_block

        return []
